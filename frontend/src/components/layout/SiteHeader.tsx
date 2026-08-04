import { Link, NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import LanguageSwitcher from "./LanguageSwitcher";

export default function SiteHeader() {
  const { t } = useTranslation();

  return (
    <header className="sticky top-0 z-40 border-b border-teal-900/8 bg-[color-mix(in_srgb,var(--color-surface)_82%,white)]/90 backdrop-blur-md">
      <div className="mx-auto flex h-[var(--header-h)] max-w-6xl items-center justify-between gap-4 px-5 sm:px-8">
        <Link
          to="/"
          className="font-display text-xl tracking-tight text-[var(--color-teal-950)] transition hover:text-[var(--color-teal-800)] sm:text-[1.35rem]"
        >
          {t("brand")}
        </Link>

        <nav className="flex items-center gap-4 sm:gap-6" aria-label="Primary">
          <NavLink
            to="/detect"
            className={({ isActive }) =>
              [
                "text-sm font-medium transition",
                isActive
                  ? "text-[var(--color-teal-800)]"
                  : "text-[var(--color-muted)] hover:text-[var(--color-teal-800)]",
              ].join(" ")
            }
          >
            {t("nav.detection")}
          </NavLink>
          <LanguageSwitcher />
        </nav>
      </div>
    </header>
  );
}
