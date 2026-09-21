import { useMemo, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminUsersApi, type IssuedSubscriptionItem } from '../api/adminUsers';
import { tariffsApi } from '../api/tariffs';
import { usePlatform } from '../platform/hooks/usePlatform';
import { useNotify } from '../platform/hooks/useNotify';
import { getApiErrorMessage } from '../utils/api-error';
import { copyToClipboard } from '../utils/clipboard';
import { BackIcon, CopyIcon, RefreshIcon } from '@/components/icons';
import { IssuedSubscriptionModal } from '../components/admin/IssuedSubscriptionModal';

export default function AdminIssuedSubscriptions() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const notify = useNotify();
  const queryClient = useQueryClient();
  const { capabilities } = usePlatform();

  const [tariffId, setTariffId] = useState<number | ''>('');
  const [days, setDays] = useState(365);
  const [count, setCount] = useState(1);
  const [note, setNote] = useState('');
  const [email, setEmail] = useState('');
  const [telegram, setTelegram] = useState('');
  const [shareItems, setShareItems] = useState<IssuedSubscriptionItem[] | null>(null);

  const tariffsQuery = useQuery({
    queryKey: ['admin-tariffs', false],
    queryFn: () => tariffsApi.getTariffs(false),
  });
  const tariffs = useMemo(
    () => (tariffsQuery.data?.tariffs ?? []).filter((item) => item.is_active && !item.is_daily),
    [tariffsQuery.data],
  );

  const listQuery = useQuery({
    queryKey: ['admin-issued-subscriptions'],
    queryFn: () => adminUsersApi.getIssuedSubscriptions({ limit: 100 }),
  });

  const issueMutation = useMutation({
    mutationFn: () =>
      adminUsersApi.issueSubscriptions({
        tariff_id: Number(tariffId),
        days,
        count: email.trim() || telegram.trim() ? 1 : count,
        note: note.trim() || undefined,
        email: email.trim() || undefined,
        telegram: telegram.trim() || undefined,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['admin-issued-subscriptions'] });
      setShareItems(data.items);
      notify.success(t('admin.issuedSubscriptions.issued', { count: data.total }));
    },
    onError: (error) => {
      notify.error(getApiErrorMessage(error, t('admin.issuedSubscriptions.issueError')));
    },
  });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!tariffId) {
      notify.error(t('admin.users.detail.subscription.selectTariff'));
      return;
    }
    issueMutation.mutate();
  };

  const items = listQuery.data?.items ?? [];

  return (
    <div className="animate-fade-in">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {!capabilities.hasBackButton && (
            <button
              type="button"
              onClick={() => navigate('/admin')}
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-dark-700 bg-dark-800 transition-colors hover:border-dark-600"
            >
              <BackIcon />
            </button>
          )}
          <div>
            <h1 className="text-xl font-bold text-dark-100">{t('admin.issuedSubscriptions.title')}</h1>
            <p className="text-sm text-dark-400">{t('admin.issuedSubscriptions.subtitle')}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => listQuery.refetch()}
          className="rounded-lg p-2 transition-colors hover:bg-dark-700"
        >
          <RefreshIcon className={listQuery.isFetching ? 'animate-spin' : ''} />
        </button>
      </div>

      <form
        onSubmit={handleSubmit}
        className="mb-6 space-y-3 rounded-xl border border-dark-700 bg-dark-800/50 p-4"
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm text-dark-300">
            {t('admin.issuedSubscriptions.tariff')}
            <select
              value={tariffId}
              onChange={(e) => setTariffId(e.target.value ? Number(e.target.value) : '')}
              className="input mt-1"
              required
            >
              <option value="">{t('admin.users.detail.subscription.selectTariff')}</option>
              {tariffs.map((tariff) => (
                <option key={tariff.id} value={tariff.id}>
                  {tariff.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm text-dark-300">
            {t('admin.issuedSubscriptions.days')}
            <input
              type="number"
              min={1}
              max={3650}
              value={days}
              onChange={(e) => setDays(Number(e.target.value) || 365)}
              className="input mt-1"
            />
          </label>
          <label className="block text-sm text-dark-300">
            {t('admin.issuedSubscriptions.count')}
            <input
              type="number"
              min={1}
              max={50}
              value={count}
              disabled={Boolean(email.trim() || telegram.trim())}
              onChange={(e) => setCount(Math.min(50, Math.max(1, Number(e.target.value) || 1)))}
              className="input mt-1"
            />
          </label>
          <label className="block text-sm text-dark-300">
            {t('admin.issuedSubscriptions.note')}
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={200}
              placeholder={t('admin.issuedSubscriptions.notePlaceholder')}
              className="input mt-1"
            />
          </label>
          <label className="block text-sm text-dark-300">
            {t('admin.issuedSubscriptions.email')}
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
              className="input mt-1"
            />
          </label>
          <label className="block text-sm text-dark-300">
            {t('admin.issuedSubscriptions.telegram')}
            <input
              value={telegram}
              onChange={(e) => setTelegram(e.target.value)}
              placeholder="@username / 123456789"
              className="input mt-1"
            />
          </label>
        </div>
        <p className="text-xs text-dark-500">{t('admin.issuedSubscriptions.formHint')}</p>
        <button type="submit" className="btn-primary" disabled={issueMutation.isPending}>
          {issueMutation.isPending
            ? t('admin.issuedSubscriptions.issuing')
            : t('admin.issuedSubscriptions.issue')}
        </button>
      </form>

      <div className="space-y-2">
        {listQuery.isLoading ? (
          <div className="flex justify-center py-10">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent-500 border-t-transparent" />
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-xl bg-dark-800/50 p-6 text-center text-sm text-dark-400">
            {t('admin.issuedSubscriptions.empty')}
          </div>
        ) : (
          items.map((item) => (
            <div
              key={item.event_id ?? `${item.user_id}-${item.issued_at}`}
              className="rounded-xl border border-dark-700 bg-dark-800/50 p-3"
            >
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <button
                  type="button"
                  className="text-left text-sm font-medium text-dark-100 hover:text-accent-400"
                  onClick={() => navigate(`/admin/users/${item.user_id}`)}
                >
                  {item.note || item.user_label || `#${item.user_id}`}
                </button>
                <span className="text-xs text-dark-500">
                  {item.tariff_name}
                  {item.expires_at ? ` · ${new Date(item.expires_at).toLocaleDateString()}` : ''}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {item.happ_link && (
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded-lg bg-dark-700 px-2 py-1 text-xs text-dark-200 hover:bg-dark-600"
                    onClick={async () => {
                      await copyToClipboard(item.happ_link!);
                      notify.success(t('admin.issuedSubscriptions.copied'));
                    }}
                  >
                    <CopyIcon /> Happ
                  </button>
                )}
                {item.subscription_url && (
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded-lg bg-dark-700 px-2 py-1 text-xs text-dark-200 hover:bg-dark-600"
                    onClick={async () => {
                      await copyToClipboard(item.subscription_url!);
                      notify.success(t('admin.issuedSubscriptions.copied'));
                    }}
                  >
                    <CopyIcon /> HTTPS
                  </button>
                )}
                <button
                  type="button"
                  className="rounded-lg bg-accent-500/15 px-2 py-1 text-xs text-accent-300 hover:bg-accent-500/25"
                  onClick={() => setShareItems([item])}
                >
                  {t('admin.issuedSubscriptions.show')}
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <IssuedSubscriptionModal
        open={Boolean(shareItems?.length)}
        items={shareItems ?? []}
        onClose={() => setShareItems(null)}
      />
    </div>
  );
}
