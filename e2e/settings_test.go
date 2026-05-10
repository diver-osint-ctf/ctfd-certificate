// Settings-flow tests for ctfd-certificate: logo upload / reset /
// scale / offset, color settings, the certificate_enabled toggle, and the
// default-logo fallback served by /admin/certificates/logo.
package e2e

import (
	"bytes"
	"net/http"
	"strings"
	"testing"

	"github.com/diver-osint-ctf/ctfd-plugin-e2e/testutil"
)

// 8x8 fully-transparent PNG, ~67 bytes. Just enough to be a valid PNG so the
// plugin's "is this PNG/JPG?" extension check accepts it and stores blob.
var tinyPNG = []byte{
	0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
	0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52,
	0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x08,
	0x08, 0x06, 0x00, 0x00, 0x00, 0xc4, 0x0f, 0xbe,
	0x8b, 0x00, 0x00, 0x00, 0x0d, 0x49, 0x44, 0x41,
	0x54, 0x78, 0x9c, 0x63, 0xfa, 0xcf, 0x00, 0x00,
	0x00, 0x02, 0x00, 0x01, 0xe5, 0x27, 0xde, 0xfc,
	0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4e, 0x44,
	0xae, 0x42, 0x60, 0x82,
}

// settingsForm builds the minimum required certificate-admin form that the
// plugin re-validates and writes back to DB on every POST.
func settingsForm(extra map[string]string) map[string]string {
	form := map[string]string{
		"certificate_enabled":  "1",
		"ctf_title":            "E2E CTF",
		"title_text":           "CERTIFICATE OF PARTICIPATION",
		"footer_text":          "Congratulations",
		"competition_phrase":   "international cybersecurity competition",
		"event_id":             "",
		"logo_scale":           "100",
		"logo_offset_x":        "0",
		"logo_offset_y":        "0",
	}
	for k, v := range extra {
		form[k] = v
	}
	return form
}

// applySettings posts the form via session admin + multipart (or plain).
// `files` may be nil when no upload is involved.
func applySettings(t *testing.T, sess *testutil.Client, fields map[string]string, files []testutil.FilePart) {
	t.Helper()
	resp, err := sess.PostMultipartWithNonce("/admin/certificates", fields, files)
	if err != nil {
		t.Fatalf("apply certificate settings: %v", err)
	}
	resp.Body.Close()
	if resp.StatusCode >= 400 && resp.StatusCode != http.StatusFound {
		t.Fatalf("apply certificate settings: HTTP %s", resp.Status)
	}
}

func TestCertificate_LogoUpload_PNG(t *testing.T) {
	sess := testutil.AdminSessionClient(t)
	t.Cleanup(func() {
		applySettings(t, sess, settingsForm(map[string]string{"reset_logo": "1"}), nil)
	})
	applySettings(t, sess, settingsForm(nil), []testutil.FilePart{{
		FieldName:   "logo_file",
		Filename:    "logo.png",
		ContentType: "image/png",
		Body:        tinyPNG,
	}})

	// Pull the logo back through the admin endpoint and assert PNG magic.
	body, resp, err := sess.GetBytes("/admin/certificates/logo")
	if err != nil {
		t.Fatalf("get logo: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("get logo: HTTP %s", resp.Status)
	}
	if !bytes.HasPrefix(body, []byte{0x89, 'P', 'N', 'G'}) {
		t.Errorf("uploaded logo did not round-trip as PNG; got %d bytes starting with %v", len(body), body[:min(len(body), 8)])
	}
}

func TestCertificate_LogoUpload_InvalidExtension(t *testing.T) {
	sess := testutil.AdminSessionClient(t)
	t.Cleanup(func() {
		applySettings(t, sess, settingsForm(map[string]string{"reset_logo": "1"}), nil)
	})
	// .gif is rejected by the plugin extension whitelist.
	applySettings(t, sess, settingsForm(nil), []testutil.FilePart{{
		FieldName:   "logo_file",
		Filename:    "logo.gif",
		ContentType: "image/gif",
		Body:        []byte{'G', 'I', 'F', '8', '9', 'a'},
	}})
	// We can only check observably: the logo should NOT be a GIF afterwards
	// — i.e. the admin endpoint still returns the previous PNG (or default).
	body, resp, err := sess.GetBytes("/admin/certificates/logo")
	if err != nil {
		t.Fatalf("get logo: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("get logo: HTTP %s", resp.Status)
	}
	if bytes.HasPrefix(body, []byte{'G', 'I', 'F'}) {
		t.Errorf("rejected .gif unexpectedly accepted as logo")
	}
}

func TestCertificate_LogoReset(t *testing.T) {
	sess := testutil.AdminSessionClient(t)
	// Upload first.
	applySettings(t, sess, settingsForm(nil), []testutil.FilePart{{
		FieldName:   "logo_file",
		Filename:    "logo.png",
		ContentType: "image/png",
		Body:        tinyPNG,
	}})
	// Now reset.
	applySettings(t, sess, settingsForm(map[string]string{"reset_logo": "1"}), nil)
	t.Cleanup(func() {
		applySettings(t, sess, settingsForm(map[string]string{"reset_logo": "1"}), nil)
	})

	// After reset the endpoint serves the bundled default logo, which is also a PNG.
	body, _, err := sess.GetBytes("/admin/certificates/logo")
	if err != nil {
		t.Fatalf("get logo: %v", err)
	}
	if !bytes.HasPrefix(body, []byte{0x89, 'P', 'N', 'G'}) {
		t.Errorf("after reset expected PNG (default), got %d bytes", len(body))
	}
}

func TestCertificate_LogoScaleAndOffset(t *testing.T) {
	sess := testutil.AdminSessionClient(t)
	t.Cleanup(func() {
		applySettings(t, sess, settingsForm(nil), nil)
	})
	applySettings(t, sess, settingsForm(map[string]string{
		"logo_scale":    "150",
		"logo_offset_x": "12",
		"logo_offset_y": "-7",
	}), nil)

	// The admin page renders the current values back into form inputs.
	resp, err := sess.HTTP.Get(sess.BaseURL + "/admin/certificates")
	if err != nil {
		t.Fatalf("get admin page: %v", err)
	}
	body, _, _ := readAll(resp)
	resp.Body.Close()
	for _, want := range []string{`name="logo_scale"`, `value="150"`, `value="12"`, `value="-7"`} {
		if !strings.Contains(body, want) {
			t.Errorf("admin page missing %q", want)
		}
	}
}

func TestCertificate_EnabledToggle(t *testing.T) {
	sess := testutil.AdminSessionClient(t)
	c := testutil.AnonClient(t)

	// Force disabled then check the public flag.
	t.Cleanup(func() { applySettings(t, sess, settingsForm(nil), nil) })
	applySettings(t, sess, settingsForm(map[string]string{"certificate_enabled": ""}), nil)
	var got struct {
		Enabled bool `json:"enabled"`
	}
	if _, err := c.GetJSON("/certificates/enabled", &got); err != nil {
		t.Fatalf("get enabled flag: %v", err)
	}
	if got.Enabled {
		t.Errorf("expected enabled=false after toggle off")
	}

	// Now flip back on.
	applySettings(t, sess, settingsForm(nil), nil)
	if _, err := c.GetJSON("/certificates/enabled", &got); err != nil {
		t.Fatalf("get enabled flag (post-toggle on): %v", err)
	}
	if !got.Enabled {
		t.Errorf("expected enabled=true after toggle on")
	}
}

func TestCertificate_DefaultLogoFallback(t *testing.T) {
	sess := testutil.AdminSessionClient(t)
	applySettings(t, sess, settingsForm(map[string]string{"reset_logo": "1"}), nil)

	body, resp, err := sess.GetBytes("/admin/certificates/logo")
	if err != nil {
		t.Fatalf("get logo: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("get logo: HTTP %s", resp.Status)
	}
	if !bytes.HasPrefix(body, []byte{0x89, 'P', 'N', 'G'}) {
		t.Errorf("default logo should be PNG, got %d bytes", len(body))
	}
}

// readAll drains an http.Response body to a string. Returns (body, n, err).
func readAll(resp *http.Response) (string, int, error) {
	if resp == nil {
		return "", 0, nil
	}
	buf := make([]byte, 0, 4096)
	tmp := make([]byte, 4096)
	for {
		n, err := resp.Body.Read(tmp)
		if n > 0 {
			buf = append(buf, tmp[:n]...)
		}
		if err != nil {
			return string(buf), len(buf), nil
		}
		if len(buf) > 1<<20 {
			return string(buf), len(buf), nil
		}
	}
}
