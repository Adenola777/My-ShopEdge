/**
 * The name of one calculator line, shared by Money and Products so the same money reads
 * the same way on both screens.
 *
 * A platform adjustment or a fee MyShopEdge does not recognise carries TikTok's own name,
 * written as words by the service ("Platform penalty", "Live specials fee"), because that is
 * the name the seller knows. Owner's instruction, 10 October 2026: until then the line read
 * "TikTok adjustment" or "Fee MyShopEdge does not recognise" with TikTok's code underneath.
 * A short note underneath still says which of the two it is. Every other line carries the
 * label the service gave it.
 */

/** @param {{ line: { label: string, category?: string | null, tiktok_fee_type?: string | null } }} props */
export function LineLabel({ line }) {
  if (!line.tiktok_fee_type) return line.label;
  return (
    <span>
      {line.label}
      <span className="rows__sub" style={{ display: "block" }}>
        {line.category === "platform_adjustment"
          ? "An adjustment TikTok made"
          : "A TikTok fee MyShopEdge does not recognise yet"}
      </span>
    </span>
  );
}
