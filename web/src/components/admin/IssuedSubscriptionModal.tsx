import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';
import { QRCodeSVG } from 'qrcode.react';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import { CheckIcon, CopyIcon, XIcon } from '@/components/icons';
import { copyToClipboard } from '@/utils/clipboard';
import { useNotify } from '@/platform/hooks/useNotify';
import type { IssuedSubscriptionItem } from '@/api/adminUsers';
import { useState } from 'react';

export type IssuedShareItem = Pick<
  IssuedSubscriptionItem,
  'happ_link' | 'subscription_url' | 'expires_at' | 'note' | 'user_id' | 'user_label'
>;

interface IssuedSubscriptionModalProps {
  open: boolean;
  items: IssuedShareItem[];
  onClose: () => void;
}

export function IssuedSubscriptionModal({ open, items, onClose }: IssuedSubscriptionModalProps) {
  const { t } = useTranslation();
  const notify = useNotify();
  const trapRef = useFocusTrap<HTMLDivElement>(open, { onEscape: onClose });
  const [copied, setCopied] = useState<string | null>(null);

  if (!open || items.length === 0) return null;

  const handleCopy = async (text: string, key: string) => {
    await copyToClipboard(text);
    setCopied(key);
    notify.success(t('admin.issuedSubscriptions.copied'));
    window.setTimeout(() => setCopied((current) => (current === key ? null : current)), 1500);
  };

  const downloadCsv = () => {
    const header = 'note,user,happ_link,subscription_url,expires_at';
    const rows = items.map((item) =>
      [item.note ?? '', item.user_label ?? String(item.user_id ?? ''), item.happ_link ?? '', item.subscription_url ?? '', item.expires_at ?? '']
        .map((value) => `"${String(value).replace(/"/g, '""')}"`)
        .join(','),
    );
    const blob = new Blob([`${header}\n${rows.join('\n')}`], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'issued-subscriptions.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const primary = items[0];
  const qrValue = primary.happ_link || primary.subscription_url || '';

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/60"
        aria-label={t('common.close', 'Закрыть')}
        onClick={onClose}
      />
      <div
        ref={trapRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="issued-sub-modal-title"
        className="relative z-10 max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-dark-700 bg-dark-900 p-5 shadow-xl"
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h3 id="issued-sub-modal-title" className="text-lg font-bold text-dark-100">
              {t('admin.issuedSubscriptions.modalTitle')}
            </h3>
            <p className="mt-1 text-sm text-dark-400">{t('admin.issuedSubscriptions.modalHint')}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-dark-400 hover:bg-dark-800 hover:text-dark-100"
          >
            <XIcon />
          </button>
        </div>

        {items.length === 1 && qrValue && (
          <div className="mb-4 flex justify-center rounded-xl bg-white p-3">
            <QRCodeSVG value={qrValue} size={168} level="L" includeMargin={false} />
          </div>
        )}

        <div className="space-y-3">
          {items.map((item, index) => {
            const key = `${item.user_id ?? index}-${index}`;
            return (
              <div key={key} className="rounded-xl bg-dark-800/70 p-3">
                {(item.note || item.user_label) && (
                  <div className="mb-2 text-xs text-dark-400">
                    {item.note || item.user_label}
                    {item.expires_at && (
                      <span className="ml-2 text-dark-500">
                        → {new Date(item.expires_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                )}
                {item.happ_link && (
                  <button
                    type="button"
                    onClick={() => handleCopy(item.happ_link!, `${key}-happ`)}
                    className="mb-2 w-full rounded-lg bg-dark-700/60 p-2 text-left hover:bg-dark-700"
                  >
                    <div className="mb-0.5 flex items-center gap-1 text-xs text-dark-500">
                      {copied === `${key}-happ` ? <CheckIcon /> : <CopyIcon />}
                      {t('admin.issuedSubscriptions.happLink')}
                    </div>
                    <div className="truncate font-mono text-xs text-dark-200">{item.happ_link}</div>
                  </button>
                )}
                {item.subscription_url && (
                  <button
                    type="button"
                    onClick={() => handleCopy(item.subscription_url!, `${key}-https`)}
                    className="w-full rounded-lg bg-dark-700/60 p-2 text-left hover:bg-dark-700"
                  >
                    <div className="mb-0.5 flex items-center gap-1 text-xs text-dark-500">
                      {copied === `${key}-https` ? <CheckIcon /> : <CopyIcon />}
                      {t('admin.issuedSubscriptions.httpsLink')}
                    </div>
                    <div className="truncate font-mono text-xs text-dark-200">
                      {item.subscription_url}
                    </div>
                  </button>
                )}
                {!item.happ_link && !item.subscription_url && (
                  <div className="text-xs text-warning-400">
                    {t('admin.issuedSubscriptions.noLink')}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          {items.length > 1 && (
            <button type="button" onClick={downloadCsv} className="btn-secondary flex-1">
              {t('admin.issuedSubscriptions.downloadCsv')}
            </button>
          )}
          <button type="button" onClick={onClose} className="btn-primary flex-1">
            {t('common.done', 'Готово')}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
