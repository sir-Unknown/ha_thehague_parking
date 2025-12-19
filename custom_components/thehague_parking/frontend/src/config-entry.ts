type HomeAssistant = {
  callWS?: <T>(msg: Record<string, unknown>) => Promise<T>;
};

export function slugifyId(value: string): string {
  return value
    .normalize("NFKD")
    .replaceAll(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replaceAll(/[^a-z0-9]+/g, "_")
    .replaceAll(/^_+|_+$/g, "");
}

export function parseMeldnummerFromTitle(title: string): string | undefined {
  const match = /\((?<id>[^)]+)\)\s*$/.exec(title);
  return match?.groups?.id?.trim() || undefined;
}

export async function resolveMeldnummerFromConfigEntry(
  hass: HomeAssistant | undefined,
  entryId: string
): Promise<string | undefined> {
  if (!hass?.callWS) return undefined;
  const entries = await hass.callWS<
    Array<{ entry_id: string; title: string; unique_id?: string | null }>
  >({
    type: "config_entries/get",
    domain: "thehague_parking",
  });
  const entry = entries.find((e) => e.entry_id === entryId);
  if (!entry) return undefined;

  if (typeof entry.unique_id === "string") {
    const uniqueId = entry.unique_id.trim();
    if (uniqueId && uniqueId.toLowerCase() !== "none") {
      return uniqueId;
    }
  }

  return parseMeldnummerFromTitle(entry.title);
}
