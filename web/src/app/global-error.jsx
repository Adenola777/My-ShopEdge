"use client";

/**
 * Shown when the root layout itself fails, so it draws its own document. Added 8 October
 * 2026. It cannot rely on the layout's fonts or styles having loaded, so it stays plain.
 */

/** @param {{ error: Error & { digest?: string }, reset: () => void }} props */
export default function GlobalError({ error, reset }) {
  return (
    <html lang="en-GB">
      <body>
        <main id="main" style={{ maxWidth: 560, margin: "64px auto", padding: "0 16px", fontFamily: "system-ui, sans-serif" }}>
          <h1>MyShopEdge could not be shown.</h1>
          <p>Nothing on your account has changed. Try again in a moment.</p>
          <p><button type="button" onClick={() => reset()}>Try again</button></p>
          {error.digest && <p>Reference: {error.digest}</p>}
        </main>
      </body>
    </html>
  );
}
