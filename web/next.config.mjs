// The legal pages are static files in public/legal/. These short addresses lead to them, so
// /privacy, /terms, /cookies and /legal all open a page rather than "not found" (10 October 2026).
export default {
  async redirects() {
    return [
      { source: "/privacy", destination: "/legal/privacy.html", permanent: false },
      { source: "/terms", destination: "/legal/terms.html", permanent: false },
      { source: "/cookies", destination: "/legal/cookies.html", permanent: false },
      { source: "/legal", destination: "/legal/privacy.html", permanent: false },
      { source: "/legal/privacy", destination: "/legal/privacy.html", permanent: false },
      { source: "/legal/terms", destination: "/legal/terms.html", permanent: false },
      { source: "/legal/cookies", destination: "/legal/cookies.html", permanent: false },
    ];
  },
};
