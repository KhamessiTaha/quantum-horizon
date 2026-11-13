export interface FeaturedTarget {
  slug: string;
  name: string;
  kind: string;
  hook: string;
}

export const FEATURED_TARGETS: FeaturedTarget[] = [
  {
    slug: "barnard",
    name: "Barnard's Star",
    kind: "Red dwarf",
    hook: "The fastest-moving star in our sky. Watch it shift between passes.",
  },
  {
    slug: "eps-indi-b",
    name: "Epsilon Indi B",
    kind: "Brown dwarf pair",
    hook: "Two brown dwarfs orbiting a nearby star, seen as one moving point.",
  },
  {
    slug: "wise-0855",
    name: "WISE 0855",
    kind: "Coldest brown dwarf",
    hook: "Barely visible, and only at the longest wavelengths.",
  },
  {
    slug: "rw-aur",
    name: "RW Aurigae",
    kind: "Young variable",
    hook: "A young star whose brightness and spectrum change over the year.",
  },
  {
    slug: "r-dra",
    name: "R Draconis",
    kind: "Mira variable",
    hook: "So bright it saturates the detector, yet its spectrum still swings.",
  },
];
