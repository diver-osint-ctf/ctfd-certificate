// Additional coverage: logo size limit, token reuse, invalid token view,
// and PDF round-trip of every text-field setting.
package e2e

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"testing"

	"github.com/diver-osint-ctf/ctfd-plugin-e2e/testutil"
)

// TestCertificate_LogoUpload_RejectsOversized — the plugin enforces a 5 MB
// upper bound on uploaded logos (__init__.py: file_size > 5*1024*1024). A 6 MB
// payload must be rejected: the round-tripped logo must NOT be the giant blob
// we just sent.
func TestCertificate_LogoUpload_RejectsOversized(t *testing.T) {
	sess := testutil.AdminSessionClient(t)
	t.Cleanup(func() {
		applySettings(t, sess, settingsForm(map[string]string{"reset_logo": "1"}), nil)
	})

	// Build a >5 MB byte slice that starts with a PNG signature so the
	// extension check accepts the filename but the size check rejects it.
	oversized := make([]byte, 6*1024*1024)
	copy(oversized, tinyPNG) // keep the magic prefix
	applySettings(t, sess, settingsForm(nil), []testutil.FilePart{{
		FieldName:   "logo_file",
		Filename:    "huge.png",
		ContentType: "image/png",
		Body:        oversized,
	}})

	body, resp, err := sess.GetBytes("/admin/certificates/logo")
	if err != nil {
		t.Fatalf("get logo: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("get logo: HTTP %s", resp.Status)
	}
	// The stored logo should be vastly smaller than what we tried to upload
	// — either the previous logo or the bundled default.
	if len(body) >= len(oversized) {
		t.Errorf("oversized upload appears to have been saved (stored=%d bytes >= sent=%d)", len(body), len(oversized))
	}
	if bytes.HasPrefix(body, oversized[:32]) {
		t.Errorf("stored logo bytes match the oversized upload prefix — size limit was not enforced")
	}
}

// TestCertificate_TokenReusedForSameTeam — calling /certificates/generate
// twice for the same team must return the same token (and therefore the
// same view_url). The plugin's TeamCertificateToken row is keyed by team_id
// and the route reuses any existing row.
func TestCertificate_TokenReusedForSameTeam(t *testing.T) {
	admin := testutil.AdminClient(t)
	sess := testutil.AdminSessionClient(t)
	ns := testutil.Namespace(t)

	var userMode struct {
		Data struct {
			Value string `json:"value"`
		} `json:"data"`
	}
	if _, err := admin.GetJSON("/api/v1/configs/user_mode", &userMode); err != nil {
		t.Fatalf("read user_mode: %v", err)
	}
	if userMode.Data.Value != "teams" {
		t.Skip("certificate generate requires teams mode")
	}

	t.Cleanup(func() { applySettings(t, sess, settingsForm(nil), nil) })
	applySettings(t, sess, settingsForm(nil), nil)

	chal := testutil.CreateChallenge(t, admin, ns, "cert", testutil.ChallengeStandard, testutil.ChallengeOpts{
		Flag:  "flag{cert}",
		Value: 100,
	})
	user := testutil.CreateUser(t, admin, ns, 1)
	uc := testutil.UserClient(t, user.Name, user.Password)
	if r := testutil.Submit(t, uc, chal.ID, "flag{cert}"); r.Status != "correct" {
		t.Fatalf("submit: %s (%s)", r.Status, r.Message)
	}

	first := readGenerateURL(t, uc)
	second := readGenerateURL(t, uc)
	if first == "" || second == "" {
		t.Fatalf("both generate calls should return a view_url, got %q / %q", first, second)
	}
	if first != second {
		t.Errorf("repeated generate for same team returned different view URLs:\n  first=%s\n  second=%s",
			first, second)
	}
}

// TestCertificate_InvalidTokenViewRejected — GET /certificates/<token> with
// a token nobody owns must not leak a real certificate. The route looks the
// token up via TeamCertificateToken.query.filter_by(token=...) and returns
// an error response when nothing is found.
func TestCertificate_InvalidTokenViewRejected(t *testing.T) {
	sess := testutil.AdminSessionClient(t)
	t.Cleanup(func() { applySettings(t, sess, settingsForm(nil), nil) })
	applySettings(t, sess, settingsForm(nil), nil)

	body, resp, err := sess.GetBytes("/certificates/this-token-does-not-exist-xyz1234567890")
	if err != nil {
		t.Fatalf("GET /certificates/<bogus>: %v", err)
	}
	if resp.StatusCode == http.StatusOK {
		t.Errorf("invalid token must not produce a 200; got 200 with %d bytes (first: %.80q)",
			len(body), string(body[:min(len(body), 80)]))
	}
	// And the body must not be a PDF (no %PDF magic).
	if bytes.HasPrefix(body, []byte("%PDF")) {
		t.Error("invalid token must not return a PDF payload")
	}
}

// TestCertificate_PDFContainsTextFieldSettings — every admin text setting
// (ctf_title, title_text, footer_text, competition_phrase) must surface in
// the rendered PDF. Skips when WeasyPrint deps are missing (sample-pdf 500).
func TestCertificate_PDFContainsTextFieldSettings(t *testing.T) {
	sess := testutil.AdminSessionClient(t)

	const (
		ctfTitle    = "Diver E2E Probe CTF"
		title       = "OFFICIAL ATTENDANCE CERT"
		footer      = "Thanks for playing the probe edition"
		competition = "diver-probe cybersecurity invitational"
	)
	t.Cleanup(func() { applySettings(t, sess, settingsForm(nil), nil) })
	applySettings(t, sess, settingsForm(map[string]string{
		"ctf_title":          ctfTitle,
		"title_text":         title,
		"footer_text":        footer,
		"competition_phrase": competition,
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
	testutil.ContainsAll(t, text, ctfTitle, title, footer, competition)
}

// readGenerateURL POSTs /certificates/generate as the given user client and
// returns the view_url field. Returns "" if the endpoint signals WeasyPrint
// is unavailable (500 path) — callers should treat this as an early skip.
func readGenerateURL(t *testing.T, uc *testutil.Client) string {
	t.Helper()
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
	raw, _ := io.ReadAll(resp.Body)
	if err := json.Unmarshal(raw, &gen); err != nil {
		t.Fatalf("decode generate: %v (body=%s)", err, raw)
	}
	if !gen.Success {
		t.Fatalf("generate cert: success=false (body=%s)", raw)
	}
	return strings.TrimSpace(gen.ViewURL)
}
