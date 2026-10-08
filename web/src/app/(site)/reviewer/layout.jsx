/**
 * Gives the reviewer sign-in page its title. The page is a client component, so it cannot
 * export `metadata` itself, and without this layout the tab read only "MyShopEdge".
 */

export const metadata = { title: "Reviewer sign-in" };

/** @param {{ children: React.ReactNode }} props */
export default function ReviewerLayout({ children }) {
  return children;
}
