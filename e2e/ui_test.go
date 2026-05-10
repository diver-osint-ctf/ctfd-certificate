package e2e

import (
	"strings"
	"testing"

	"github.com/diver-osint-ctf/ctfd-plugin-e2e/testutil"
)

// TestCertificate_AdminPageRendersInBrowser drives a real browser via
// agent-browser. It is a smoke check that the certificate admin template
// loads end-to-end (HTML render + JS init) — the API-only test cannot
// catch JS errors that block the page.
func TestCertificate_AdminPageRendersInBrowser(t *testing.T) {
	base := testutil.CTFdURL(t)
	b := testutil.NewBrowser(t)

	b.Open(base + "/login")
	b.Wait("input[name=name]")
	b.Type("input[name=name]", testutil.AdminName(t))
	b.Type("input[name=password]", testutil.AdminPassword(t))
	// CTFd's login form is rendered with WTForms SubmitField which emits an
	// <input type="submit">, not <button type="submit">.
	b.Click("input[type=submit]")

	b.Open(base + "/admin/certificates")
	b.Wait("body")

	body := b.GetText("body")
	if !strings.Contains(strings.ToLower(body), "certificate") {
		b.Screenshot("")
		t.Errorf("expected the word \"certificate\" somewhere on the page; saved screenshot. body excerpt=%q", trunc(body, 200))
	}
}

func trunc(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}
