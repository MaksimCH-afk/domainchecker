import type { AnalyzeResponse, Config, UploadStats } from "./types";

async function jsonOrThrow(res: Response) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  async getDefaultConfig(): Promise<Config> {
    return (await jsonOrThrow(await fetch("/api/config/default"))).config;
  },

  async validateConfig(config: Config): Promise<{ config: Config; warnings: string[] }> {
    return jsonOrThrow(
      await fetch("/api/config/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config }),
      })
    );
  },

  async uploadFile(file: File): Promise<UploadStats> {
    const fd = new FormData();
    fd.append("file", file);
    return jsonOrThrow(
      await fetch("/api/ahrefs/datasets", { method: "POST", body: fd })
    );
  },

  async analyze(datasetId: string, config: Config): Promise<AnalyzeResponse> {
    return jsonOrThrow(
      await fetch(`/api/ahrefs/datasets/${datasetId}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config }),
      })
    );
  },

  async exportBlob(
    datasetId: string,
    config: Config,
    format: "csv" | "txt",
    includeRaw: boolean
  ): Promise<Blob> {
    const res = await fetch(`/api/ahrefs/datasets/${datasetId}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config, format, include_raw: includeRaw }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.blob();
  },

  async bridgeTargets(
    datasetId: string,
    config: Config,
    tiers: string[]
  ): Promise<{ count: number; targets: string[] }> {
    return jsonOrThrow(
      await fetch(
        `/api/ahrefs/datasets/${datasetId}/targets?tiers=${tiers.join(",")}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ config }),
        }
      )
    );
  },

  async listPresets(): Promise<string[]> {
    return (await jsonOrThrow(await fetch("/api/config/presets"))).presets;
  },

  async savePreset(name: string, config: Config): Promise<void> {
    await jsonOrThrow(
      await fetch("/api/config/presets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, config }),
      })
    );
  },

  async getPreset(name: string): Promise<Config> {
    return (
      await jsonOrThrow(await fetch(`/api/config/presets/${encodeURIComponent(name)}`))
    ).config;
  },

  async deletePreset(name: string): Promise<void> {
    await jsonOrThrow(
      await fetch(`/api/config/presets/${encodeURIComponent(name)}`, {
        method: "DELETE",
      })
    );
  },
};
