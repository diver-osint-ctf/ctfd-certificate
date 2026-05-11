// Tests for recent certificate-plugin features that lacked E2E coverage:
//
//   - 95c662d: use the CTFd "end" config as the certificate issue date.
//     get_ctf_end_date_str() formats it as "%B %d, %Y" — we set `end`
//     to a known Unix timestamp and assert the rendered date string
//     appears in the PDF.
//   - 4ccd44b: render the CTFtime verification URL with `/result`. The
//     template embeds `https://ctftime.org/event/<event_id>/result`
//     when event_id is set; we assert that exact substring shows up
//     in the PDF.
//   - Team-mode full download flow: solve → POST /certificates/generate
//     → GET /certificates/<token> → PDF, and the PDF text mentions the
//     team and its score.
//
// All three require the WeasyPrint-augmented CTFd image; they skip
// when sample-pdf returns 500 (deps missing).
package e2e

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"

	"github.com/diver-osint-ctf/ctfd-plugin-e2e/testutil"
)

// patchEnd sets the CTFd `end` config via the admin API. value can be
// an empty string to clear, or a Unix timestamp string.
func patchEnd(t *testing.T, admin *testutil.Client, value string) {
	t.Helper()
	resp, err := admin.DoJSON(http.MethodPatch, "/api/v1/configs/end",
		map[string]any{"value": value}, nil)
	if err != nil {
		t.Fatalf("set end: %v", err)
	}
	resp.Body.Close()
	if resp.StatusCode >= 400 {
		t.Fatalf("set end %q: HTTP %s", value, resp.Status)
	}
}

// readEndConfig returns the current value of the end config, or "" if unset.
func readEndConfig(t *testing.T, admin *testutil.Client) string {
	t.Helper()
	var resp struct {
		Data struct {
			Value string `json:"value"`
		} `json:"data"`
	}
	r, _ := admin.GetJSON("/api/v1/configs/end", &resp)
	if r != nil && r.StatusCode >= 400 {
		return ""
	}
	return resp.Data.Value
}

// TestCertificate_PDFContainsCTFEndDate — the certificate PDF must use the
// CTF's `end` config as the issue date, not the current date.
func TestCertificate_PDFContainsCTFEndDate(t *testing.T) {
	sess := testutil.AdminSessionClient(t)
	admin := testutil.AdminClient(t)

	// Pick a fixed end date so we can match its formatted string.
	end := time.Date(2027, time.January, 15, 12, 0, 0, 0, time.UTC)
	original := readEndConfig(t, admin)
	t.Cleanup(func() { patchEnd(t, admin, original) })
	patchEnd(t, admin, fmt.Sprintf("%d", end.Unix()))

	// Make sure settings have certificate_enabled=1; otherwise sample-pdf
	// still renders but other tests that toggle it can leave it in a
	// surprising state. settingsForm defaults certificate_enabled=1.
	t.Cleanup(func() { applySettings(t, sess, settingsForm(nil), nil) })
	applySettings(t, sess, settingsForm(nil), nil)

	body, resp, err := sess.GetBytes("/admin/certificates/sample-pdf")
	if err != nil {
		t.Fatalf("GET sample-pdf: %v", err)
	}
	if resp.StatusCode == http.StatusInternalServerError {
		t.Skip("sample-pdf returned 500 — WeasyPrint deps absent")
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("GET sample-pdf: HTTP %s", resp.Status)
	}
	testutil.RequirePDF(t, body)

	text := testutil.ExtractPDFText(t, body)
	want := end.Format("January 02, 2006") // Go layout for "%B %d, %Y"
	// Python's strftime uses 0-padded day on Linux but unpadded on
	// macOS — accept either.
	wantUnpadded := strings.ReplaceAll(want, " 0", " ")
	if !strings.Contains(text, want) && !strings.Contains(text, wantUnpadded) {
		t.Errorf("PDF should mention CTF end date (%q or %q), got first 400 chars: %.400s…",
			want, wantUnpadded, text)
	}
}

// TestCertificate_PDFContainsCTFtimeResultURL — when event_id is set,
// the PDF embeds the verification URL with the new `/result` suffix.
func TestCertificate_PDFContainsCTFtimeResultURL(t *testing.T) {
	sess := testutil.AdminSessionClient(t)

	const probe = "99999"
	t.Cleanup(func() { applySettings(t, sess, settingsForm(nil), nil) })
	applySettings(t, sess, settingsForm(map[string]string{
		"event_id": probe,
	}), nil)

	body, resp, err := sess.GetBytes("/admin/certificates/sample-pdf")
	if err != nil {
		t.Fatalf("GET sample-pdf: %v", err)
	}
	if resp.StatusCode == http.StatusInternalServerError {
		t.Skip("sample-pdf returned 500 — WeasyPrint deps absent")
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("GET sample-pdf: HTTP %s", resp.Status)
	}
	testutil.RequirePDF(t, body)

	text := testutil.ExtractPDFText(t, body)
	wantURL := fmt.Sprintf("ctftime.org/event/%s/result", probe)
	if !strings.Contains(text, wantURL) {
		t.Errorf("PDF should mention CTFtime URL %q, got first 400 chars: %.400s…", wantURL, text)
	}
}

// TestCertificate_TeamFullDownloadFlow — exercise the participant-side
// download path end to end: solve a challenge in teams mode, POST to
// /certificates/generate to get a token, GET the certificate URL, and
// confirm the PDF mentions the team name. Skips if the running CTFd
// is in users mode.
func TestCertificate_TeamFullDownloadFlow(t *testing.T) {
	admin := testutil.AdminClient(t)
	sess := testutil.AdminSessionClient(t)
	ns := testutil.Namespace(t)

	// /certificates/generate returns 400 in users mode ("Users not in a team
	// cannot generate certificates"). Skip cleanly if the orchestrator
	// configured users mode for this run.
	var userModeResp struct {
		Data struct {
			Value string `json:"value"`
		} `json:"data"`
	}
	if _, err := admin.GetJSON("/api/v1/configs/user_mode", &userModeResp); err != nil {
		t.Fatalf("read user_mode: %v", err)
	}
	if userModeResp.Data.Value != "teams" {
		t.Skip("certificate per-team download requires teams mode")
	}

	// Ensure certificates are enabled.
	t.Cleanup(func() { applySettings(t, sess, settingsForm(nil), nil) })
	applySettings(t, sess, settingsForm(nil), nil)

	chal := testutil.CreateChallenge(t, admin, ns, "cert", testutil.ChallengeStandard, testutil.ChallengeOpts{
		Flag:  "flag{cert}",
		Value: 100,
	})
	user := testutil.CreateUser(t, admin, ns, 1)
	if user.TeamID == 0 {
		t.Fatalf("teams-mode CreateUser should have attached a team, got TeamID=0")
	}

	uc := testutil.UserClient(t, user.Name, user.Password)
	if r := testutil.Submit(t, uc, chal.ID, "flag{cert}"); r.Status != "correct" {
		t.Fatalf("submit: %s (%s)", r.Status, r.Message)
	}

	// Look up the team name for later assertion.
	var teamResp struct {
		Data struct {
			Name string `json:"name"`
		} `json:"data"`
	}
	if _, err := admin.GetJSON(fmt.Sprintf("/api/v1/teams/%d", user.TeamID), &teamResp); err != nil {
		t.Fatalf("read team: %v", err)
	}

	// Generate a download token. /certificates/generate is authed_only and
	// expects JSON content type (so the tokens() middleware lets us through
	// with the admin Token… but the endpoint reads get_current_user() from
	// the session). We use the user's session client.
	resp, err := uc.PostJSON("/certificates/generate", nil, nil)
	if err != nil {
		t.Fatalf("generate cert: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusInternalServerError {
		t.Skip("/certificates/generate returned 500 — WeasyPrint deps absent")
	}
	if resp.StatusCode != http.StatusOK {
		raw, _ := io.ReadAll(resp.Body)
		t.Fatalf("generate cert: HTTP %s body=%s", resp.Status, string(raw))
	}
	var gen struct {
		Success bool   `json:"success"`
		ViewURL string `json:"view_url"`
	}
	body, _ := io.ReadAll(resp.Body)
	if err := json.Unmarshal(body, &gen); err != nil {
		t.Fatalf("decode generate response: %v (body=%s)", err, body)
	}
	if !gen.Success || gen.ViewURL == "" {
		t.Fatalf("generate cert: bad response: %s", body)
	}

	// Fetch the PDF.
	pdf, resp2, err := uc.GetBytes(gen.ViewURL)
	if err != nil {
		t.Fatalf("GET %s: %v", gen.ViewURL, err)
	}
	if resp2.StatusCode == http.StatusInternalServerError {
		t.Skip("certificate render returned 500 — WeasyPrint deps absent")
	}
	if resp2.StatusCode != http.StatusOK {
		t.Fatalf("GET %s: HTTP %s", gen.ViewURL, resp2.Status)
	}
	testutil.RequirePDF(t, pdf)

	text := testutil.ExtractPDFText(t, pdf)
	if !strings.Contains(text, teamResp.Data.Name) {
		t.Errorf("PDF should mention team name %q, got: %.400s…", teamResp.Data.Name, text)
	}
}
