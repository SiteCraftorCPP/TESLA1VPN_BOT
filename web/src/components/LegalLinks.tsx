import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';

interface LegalLinksProps {
  className?: string;
}

export default function LegalLinks({ className = '' }: LegalLinksProps) {
  const { t } = useTranslation();

  return (
    <nav
      className={`flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-xs text-dark-500 ${className}`}
      aria-label={t('legal.navLabel', 'Legal documents')}
    >
      <Link to="/info?tab=privacy" className="transition-colors hover:text-accent-400">
        {t('info.privacy')}
      </Link>
      <span aria-hidden className="text-dark-600">
        ·
      </span>
      <Link to="/info?tab=offer" className="transition-colors hover:text-accent-400">
        {t('info.offer')}
      </Link>
    </nav>
  );
}
