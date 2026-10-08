"use client";

/**
 * Where the browser lands when the bank insisted on a redirect while checking a new card.
 * Stripe adds `setup_intent` to the address; this page finishes the change with setCard.
 * Added 8 October 2026.
 */

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { saveCard } from "../CardChangeForm";

export default function CardDonePage() {
  return (
    <section className="billing">
      <Suspense fallback={<p aria-live="polite">One moment.</p>}>
        <Finish />
      </Suspense>
    </section>
  );
}

function Finish() {
  const params = useSearchParams();
  const [state, setState] = useState(/** @type {"saving" | "saved" | string} */ ("saving"));

  useEffect(() => {
    const id = params.get("setup_intent") ?? undefined;
    saveCard(id).then((err) => setState(err ?? "saved"));
  }, [params]);

  if (state === "saving") return <p aria-live="polite">Saving your new card.</p>;
  if (state === "saved") {
    return (
      <section className="card-step card-step--done" aria-live="polite">
        <h1>Your new card is saved.</h1>
        <p>Your plan will charge this card from its next payment. Nothing has been charged today.</p>
        <Link className="btn btn--primary btn--block" href="/shops">Back to your shop</Link>
      </section>
    );
  }
  return (
    <section className="card-step">
      <h1>Your card was not changed.</h1>
      <p role="alert">{state}</p>
      <Link className="btn btn--primary btn--block" href="/billing/card">Try again</Link>
    </section>
  );
}
