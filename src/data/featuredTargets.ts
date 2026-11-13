import type { DetectorId } from "../lib/viewState.ts";

export interface FeaturedTarget {
  slug: string;
  name: string;
  kind: string;
  hook: string;
  detector: DetectorId;
  /** Why this detector: SPHEREx splits 0.75–5 µm across six, and the right one decides whether a source shows at all. */
  detectorReason: string;
  expect: string;
}

export const FEATURED_TARGETS: FeaturedTarget[] = [
  {
    slug: "barnard",
    name: "Barnard's Star",
    kind: "Red dwarf · 1.8 pc",
    hook: "The fastest-moving star in our sky. Watch it shift between passes.",
    detector: "D2",
    detectorReason: "bright across the near infrared",
    expect: "About 10″ of motion in a year, under two SPHEREx pixels, measured against the catalog prediction.",
  },
  {
    slug: "eps-indi-b",
    name: "Epsilon Indi B",
    kind: "Brown dwarf pair · 3.6 pc",
    hook: "Two brown dwarfs orbiting a nearby star, seen as one moving point.",
    detector: "D5",
    detectorReason: "brown dwarfs are brightest at 3.8–4.4 µm",
    expect: "The pair is under 1″ apart, so SPHEREx sees one source. Expect roughly 7″ of motion over the survey.",
  },
  {
    slug: "wise-0855",
    name: "WISE 0855−0714",
    kind: "Coldest known brown dwarf · 2.3 pc",
    hook: "Barely visible, and only at the longest wavelengths.",
    detector: "D6",
    detectorReason: "almost nothing escapes below 3.5 µm",
    expect: "A marginal detection at best. This is the honest limit of what SPHEREx can do today, and it is labelled as such.",
  },
  {
    slug: "rw-aur",
    name: "RW Aurigae",
    kind: "Young variable star",
    hook: "A young star whose brightness and spectrum change over the year.",
    detector: "D1",
    detectorReason: "the dimming is strongest at the shortest wavelengths",
    expect: "Brightness changes by tens of per cent between passes, and more at short wavelengths than long.",
  },
  {
    slug: "r-dra",
    name: "R Draconis",
    kind: "Mira variable · deep field",
    hook: "So bright it saturates the detector, yet its spectrum still swings.",
    detector: "D1",
    detectorReason: "coolest bands carry the Mira's strongest signal",
    expect: "Near the north ecliptic pole, so SPHEREx revisits it constantly. Saturated, and the tool says so rather than quoting a brightness.",
  },
];

export function viewLink(target: FeaturedTarget): string {
  return `/view?target=${encodeURIComponent(target.name)}&det=${target.detector}&fov=0.06&mode=blink`;
}
