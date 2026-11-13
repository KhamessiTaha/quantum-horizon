import { Link } from "react-router-dom";
import Badge from "../components/Badge.tsx";
import SearchBox from "../components/SearchBox.tsx";
import { FEATURED_TARGETS } from "../data/featuredTargets.ts";
import styles from "./Landing.module.css";

const STEPS = [
  {
    n: "01 · Find",
    title: "Every image of that spot",
    body: "Queries the NASA/IPAC archive for every SPHEREx exposure covering your position, including the latest weekly release.",
  },
  {
    n: "02 · Align",
    title: "One grid, one moment",
    body: "Reprojects every frame onto a common grid and moves catalog positions to each frame's date, so only real changes remain.",
  },
  {
    n: "03 · Measure",
    title: "Numbers you can trust",
    body: "Motion, brightness and spectrum over time, each with an uncertainty and a plain label for how far the data can be trusted.",
  },
];

export default function Landing() {
  return (
    <main>
      <section className={`container ${styles.hero}`}>
        <div className={styles.heroText}>
          <p className={`mono ${styles.eyebrow}`}>NASA SPHEREx · 102 infrared bands · the whole sky every six months</p>
          <h1 className={styles.title}>
            Blink the infrared sky.
            <br />
            Measure what moved.
          </h1>
          <p className={styles.lead}>
            In 1930, Pluto was found by comparing two photographs of the same patch of sky. Quantum Horizon does the
            same with every SPHEREx image of any position you choose, then tells you how far things moved, how they
            changed, and how sure that measurement is.
          </p>
          <SearchBox />
        </div>
        <figure className={styles.heroFigure}>
          <div className={styles.strip}>
            {["Pass 1", "Pass 2", "Pass 3", "Difference"].map((label) => (
              <div key={label} className={styles.stripItem}>
                <div className={styles.framePlaceholder} role="img" aria-label={`${label} image placeholder`} />
                <span className="mono">{label}</span>
              </div>
            ))}
          </div>
          <figcaption className={`panel ${styles.caption}`}>
            <span>Featured target · detector 2 · three passes</span>
            <span className="mono">Placeholder until the backend serves frames</span>
          </figcaption>
        </figure>
      </section>

      <section id="targets" className={`container ${styles.targets}`}>
        <div className={styles.sectionHead}>
          <h2>Start with a test target</h2>
          <p>The five sources named in the challenge.</p>
        </div>
        <div className={styles.cards}>
          {FEATURED_TARGETS.map((t) => (
            <Link key={t.slug} to={`/view?target=${encodeURIComponent(t.name)}`} className={`panel ${styles.card}`}>
              <span className={`mono ${styles.kind}`}>{t.kind}</span>
              <span className={styles.cardName}>{t.name}</span>
              <span className={styles.hook}>{t.hook}</span>
              <Badge confidence="pending" />
            </Link>
          ))}
        </div>
      </section>

      <section id="how" className={styles.band}>
        <div className={`container ${styles.how}`}>
          <h2>Every blink becomes a measurement</h2>
          <ol className={styles.steps}>
            {STEPS.map((s) => (
              <li key={s.n}>
                <span className={`mono ${styles.stepN}`}>{s.n}</span>
                <span className={styles.stepTitle}>{s.title}</span>
                <span className={styles.stepBody}>{s.body}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <footer id="data" className={`container ${styles.footer}`}>
        <p>
          Images: NASA/JPL-Caltech/IPAC, SPHEREx Quick Release via the NASA/IPAC Infrared Science Archive. Positions and
          motions: SIMBAD (CDS) and Gaia DR3 (ESA). Results are labelled measurements or candidates, never discoveries.
        </p>
        <p>NASA Space Apps 2026 · Planet X and SPHEREx</p>
      </footer>
    </main>
  );
}
