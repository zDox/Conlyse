import React, { useEffect, useRef, useState } from 'react';
import styles from './StatsSidebar.module.css';

interface SidebarItem {
  id: string;
  label: string;
}

interface SidebarSection {
  id: string;
  label: string;
  items: SidebarItem[];
}

const SECTIONS: SidebarSection[] = [
  {
    id: 'section-global',
    label: 'Global Overview',
    items: [
      { id: 'chart-global-duration',  label: 'Game Duration' },
      { id: 'chart-global-victory',   label: 'Victory Types' },
      { id: 'chart-global-traitors',  label: 'Traitor Wins' },
      { id: 'chart-global-dropout',   label: 'Player Dropout' },
      { id: 'chart-global-diplomacy', label: 'Diplomacy' },
      { id: 'chart-global-activity',  label: 'Player Activity' },
    ],
  },
  {
    id: 'section-countries',
    label: 'Country Performance',
    items: [
      { id: 'chart-countries-vp',             label: 'VP Progression' },
      { id: 'chart-countries-winrate',        label: 'Win Rate' },
      { id: 'chart-countries-territory',      label: 'Territory Control' },
      { id: 'chart-countries-placement',      label: 'Avg Placement' },
      { id: 'chart-countries-elimination',    label: 'Elimination Rate' },
      { id: 'chart-countries-expansion',      label: 'Territory Expansion' },
      { id: 'chart-countries-aggressiveness', label: 'Aggressiveness' },
      { id: 'chart-countries-diplomacy',      label: 'Diplomatic Activity' },
    ],
  },
  {
    id: 'section-economic',
    label: 'Economic Overview',
    items: [
      { id: 'chart-economic-total',      label: 'Production per Game' },
      { id: 'chart-economic-money',      label: 'Money by Country' },
      { id: 'chart-economic-rate',       label: 'Production Rate' },
      { id: 'chart-economic-timeseries', label: 'Rate over Time' },
    ],
  },
  {
    id: 'section-provinces',
    label: 'Province Analysis',
    items: [
      { id: 'chart-provinces-strategic', label: 'Strategic Map' },
    ],
  },
  {
    id: 'section-buildings',
    label: 'Building Analysis',
    items: [
      { id: 'chart-buildings-frequency',   label: 'Building Frequency' },
      { id: 'chart-buildings-win',         label: 'Win Correlation' },
      { id: 'chart-buildings-country',     label: 'Country Loadouts' },
      { id: 'chart-buildings-progression', label: 'Build Progression' },
    ],
  },
];

function scrollTo(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  const navbarHeight = parseInt(
    getComputedStyle(document.documentElement).getPropertyValue('--ifm-navbar-height') || '60',
  );
  const top = el.getBoundingClientRect().top + window.scrollY - navbarHeight - 64;
  window.scrollTo({ top, behavior: 'smooth' });
}

export default function StatsSidebar() {
  const [activeSection, setActiveSection] = useState<string>(SECTIONS[0].id);
  const [activeItem, setActiveItem] = useState<string | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    const allIds = SECTIONS.flatMap((s) => [s.id, ...s.items.map((i) => i.id)]);
    const visible = new Map<string, number>();

    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          visible.set(entry.target.id, entry.intersectionRatio);
        }
        let bestId: string | null = null;
        let bestTop = Infinity;
        for (const [id, ratio] of visible) {
          if (ratio <= 0) continue;
          const el = document.getElementById(id);
          if (!el) continue;
          const top = el.getBoundingClientRect().top;
          if (top < bestTop) {
            bestTop = top;
            bestId = id;
          }
        }
        if (!bestId) return;
        const section = SECTIONS.find(
          (s) => s.id === bestId || s.items.some((i) => i.id === bestId),
        );
        if (section) setActiveSection(section.id);
        const isItem = SECTIONS.some((s) => s.items.some((i) => i.id === bestId));
        setActiveItem(isItem ? bestId : null);
      },
      { rootMargin: '0px 0px -60% 0px', threshold: [0, 0.1, 0.5, 1] },
    );

    for (const id of allIds) {
      const el = document.getElementById(id);
      if (el) observerRef.current.observe(el);
    }

    return () => observerRef.current?.disconnect();
  }, []);

  return (
    <nav className={`menu thin-scrollbar ${styles.sidebar}`} aria-label="Statistics sections">
      <ul className="menu__list">
        {SECTIONS.map((section) => (
          <li key={section.id} className="menu__list-item">
            <a
              className={`menu__link menu__link--sublist${activeSection === section.id ? ' menu__link--active' : ''}`}
              href={`#${section.id}`}
              onClick={(e) => { e.preventDefault(); scrollTo(section.id); }}
            >
              {section.label}
            </a>
            <ul className="menu__list">
              {section.items.map((item) => (
                <li key={item.id} className="menu__list-item">
                  <a
                    className={`menu__link${activeItem === item.id ? ' menu__link--active' : ''}`}
                    href={`#${item.id}`}
                    onClick={(e) => { e.preventDefault(); scrollTo(item.id); }}
                  >
                    {item.label}
                  </a>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </nav>
  );
}
