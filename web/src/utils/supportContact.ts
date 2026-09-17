/**
 * Build a t.me URL for a Telegram user (not a bot).
 * Mini App openTelegramLink() returns to the host bot — callers must use openLink().
 */
export function supportUserChatUrl(username: string | null | undefined): string | null {
  if (!username) return null;
  const handle = username.trim().replace(/^@+/u, '');
  if (!/^[A-Za-z0-9_]{5,32}$/.test(handle)) return null;
  return `https://t.me/${handle}`;
}
