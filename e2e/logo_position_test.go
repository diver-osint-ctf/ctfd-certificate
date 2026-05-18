// PDF-effect tests for the logo position settings. Settings persistence
// (settings_test.go) only proves that logo_scale / logo_offset_x / logo_offset_y
// round-trip through the admin form. These tests prove the values actually
// influence WeasyPrint's render — re-rendering at a different scale or offset
// must produce a different PDF blob.
//
// Skips when WeasyPrint is unavailable (sample-pdf returns 500), same pattern
// as feature_test.go.
package e2e

import (
	"bytes"
	"net/http"
	"testing"

	"github.com/diver-osint-ctf/ctfd-plugin-e2e/testutil"
)

// fetchSamplePDF renders the admin sample-pdf with the current settings
// and returns the response bytes. Skips the calling test if WeasyPrint is
// not available in this CTFd image.
func fetchSamplePDF(t *testing.T, sess *testutil.Client) []byte {
	t.Helper()
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
	return body
}

// TestCertificate_LogoScaleChangesPDF — re-rendering the sample certificate
// at a wildly different logo_scale must produce a different PDF blob. We
// don't have a way to read the rendered image dimensions back out, but if
// the scale setting did nothing, the two renders would be byte-identical.
func TestCertificate_LogoScaleChangesPDF(t *testing.T) {
	sess := testutil.AdminSessionClient(t)
	t.Cleanup(func() { applySettings(t, sess, settingsForm(nil), nil) })

	// Render at default scale (100%).
	applySettings(t, sess, settingsForm(map[string]string{"logo_scale": "100"}), nil)
	basePDF := fetchSamplePDF(t, sess)

	// Render at 300% — same template, only logo size changed.
	applySettings(t, sess, settingsForm(map[string]string{"logo_scale": "300"}), nil)
	scaledPDF := fetchSamplePDF(t, sess)

	if bytes.Equal(basePDF, scaledPDF) {
		t.Errorf("PDF is byte-identical at logo_scale=100 and logo_scale=300; setting appears to have no effect (%d bytes)", len(basePDF))
	}
}

// TestCertificate_LogoOffsetChangesPDF — same idea for the X/Y offsets.
// Combine both so we don't depend on either one in isolation having a
// rendering effect (e.g. if a future revision merges offset_x into offset_y).
func TestCertificate_LogoOffsetChangesPDF(t *testing.T) {
	sess := testutil.AdminSessionClient(t)
	t.Cleanup(func() { applySettings(t, sess, settingsForm(nil), nil) })

	applySettings(t, sess, settingsForm(map[string]string{
		"logo_offset_x": "0",
		"logo_offset_y": "0",
	}), nil)
	basePDF := fetchSamplePDF(t, sess)

	applySettings(t, sess, settingsForm(map[string]string{
		"logo_offset_x": "120",
		"logo_offset_y": "80",
	}), nil)
	shiftedPDF := fetchSamplePDF(t, sess)

	if bytes.Equal(basePDF, shiftedPDF) {
		t.Errorf("PDF is byte-identical at offset (0,0) and (120,80); offset settings appear to have no effect (%d bytes)", len(basePDF))
	}
}
