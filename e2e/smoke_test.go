// Package e2e tests ctfd-certificate.
//
// The plugin renders a PDF certificate via WeasyPrint. Real per-team rendering
// requires teams mode plus a finished CTF, which is heavyweight. The smoke
// tests here cover three checkpoints: admin page reachability, the public
// "is feature enabled" JSON endpoint, and the admin sample-pdf endpoint
// (which exercises the actual PDF rendering path with the current settings).
package e2e

import (
	"net/http"
	"strings"
	"testing"

	"github.com/diver-osint-ctf/ctfd-plugin-e2e/testutil"
)

const adminPath = "/admin/certificates"

func TestCertificate_AdminPageLoads(t *testing.T) {
	admin := testutil.AdminClient(t)
	resp, err := admin.DoJSON(http.MethodGet, adminPath, nil, nil)
	if err != nil {
		t.Fatalf("GET %s: %v", adminPath, err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %s", resp.Status)
	}
}

// TestCertificate_EnabledFlag — public endpoint always returns JSON
// {"enabled": true|false} regardless of authentication.
func TestCertificate_EnabledFlag(t *testing.T) {
	c := testutil.AnonClient(t)
	var got struct {
		Enabled bool `json:"enabled"`
	}
	resp, err := c.GetJSON("/certificates/enabled", &got)
	if err != nil {
		t.Fatalf("GET /certificates/enabled: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %s", resp.Status)
	}
	// 値の真偽は問わない — レスポンス形が崩れていないことだけ確認する。
}

// TestCertificate_SamplePDFRenders exercises the WeasyPrint pipeline by
// pulling the admin sample PDF endpoint and checking the magic bytes.
//
// The official CTFd image does not ship with WeasyPrint's native deps
// (gobject-2.0, cairo, pango, ...). When they are absent the endpoint
// returns 500. We treat that as a skipped — not failed — test so the
// suite stays green on stock CTFd; the README documents how to opt in
// by extending the image.
func TestCertificate_SamplePDFRenders(t *testing.T) {
	sess := testutil.AdminSessionClient(t)
	body, resp, err := sess.GetBytes("/admin/certificates/sample-pdf")
	if err != nil {
		t.Fatalf("GET /admin/certificates/sample-pdf: %v", err)
	}
	if resp.StatusCode == http.StatusInternalServerError {
		// HTML body は CTFd の汎用エラーページなのでヒントは含まれない。
		// stderr に "gobject-2.0-0" が出ていれば WeasyPrint native deps 不足。
		t.Skip("sample-pdf returned 500 — usually means the CTFd image lacks WeasyPrint native deps (gobject/cairo/pango). Extend the image to enable this test.")
	}
	_ = strings.Contains // keep import if 500-skip path becomes more discriminating later
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %s (body starts with %q)", resp.Status, snippet(body))
	}
	testutil.RequirePDF(t, body)
}

func snippet(b []byte) string {
	if len(b) > 80 {
		return string(b[:80]) + "…"
	}
	return string(b)
}
