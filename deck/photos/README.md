# Team photos

Drop one image per person here, named to match the `photo` field in the
`TEAM` array at the top of `../build_deck.js`:

    p1.jpg  p2.jpg  p3.jpg  p4.jpg

Then rebuild:

    cd deck && node build_deck.js

**Anyone without a photo file renders a monogram avatar instead** (their
initials in a mint-ringed circle), so the slide always looks finished — add
photos as they arrive rather than waiting for all four.

Guidance:
- Square or near-square crops work best; the image is centre-cropped to a
  circle, so anything far from square loses its edges.
- ~600x600 px or larger. Smaller looks soft when projected.
- JPG or PNG.

This folder is committed but the images themselves are git-ignored — team
photos are personal data, so each person adds their own locally rather than
pushing it to a public repository.
