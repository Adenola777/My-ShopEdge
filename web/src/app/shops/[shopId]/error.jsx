"use client";

import { RouteError } from "@/components/RouteStates";

/** @param {{ error: Error & { digest?: string }, reset: () => void }} props */
export default function ErrorPage({ error, reset }) {
  return <RouteError error={error} reset={reset} />;
}
