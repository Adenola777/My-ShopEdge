import Link from "next/link";

export const metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <section>
      <h1>This page does not exist.</h1>
      <p><Link href="/">Go to the overview</Link></p>
    </section>
  );
}
