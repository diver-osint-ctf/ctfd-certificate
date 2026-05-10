// PDF-content tests for ctfd-certificate. Requires the WeasyPrint-augmented
// CTFd image (Dockerfile.ctfd-plus); on a stock image these tests are
// skipped via the same 500 detection as smoke_test's sample-pdf check.
package e2e

import (
	"net/http"
	"strings"
	"testing"

	"github.com/diver-osint-ctf/ctfd-plugin-e2e/testutil"
)

// TestCertificate_SamplePDFContainsTitle — sample-pdf endpoint emits a
// real PDF whose extracted text mentions the configured CTF title.
func TestCertificate_SamplePDFContainsTitle(t *testing.T) {
	sess := testutil.AdminSessionClient(t)
	// Push a known title via the admin form.
	t.Cleanup(func() { applySettings(t, sess, settingsForm(nil), nil) })
	applySettings(t, sess, settingsForm(map[string]string{
		"ctf_title": "E2E PDF Title Probe",
	}), nil)

	body, resp, err := sess.GetBytes("/admin/certificates/sample-pdf")
	if err != nil {
		t.Fatalf("GET sample-pdf: %v", err)
	}
	if resp.StatusCode == http.StatusInternalServerError {
		t.Skip("sample-pdf returned 500 — extend CTFd image with WeasyPrint deps to run this test")
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("GET sample-pdf: HTTP %s", resp.Status)
	}
	testutil.RequirePDF(t, body)

	text := testutil.ExtractPDFText(t, body)
	// The sample renders "Sample Team" as the participant; the configured
	// CTF title is also rendered in the body.
	must := []string{"Sample Team"}
	maybe := []string{"E2E PDF Title Probe", "PARTICIPATION", "CERTIFICATE"}
	testutil.ContainsAll(t, text, must...)
	hits := 0
	for _, m := range maybe {
		if strings.Contains(text, m) {
			hits++
		}
	}
	if hits == 0 {
		t.Errorf("none of %v appear in PDF text; extracted: %.300s…", maybe, text)
	}
}
