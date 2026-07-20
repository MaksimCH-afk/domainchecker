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

  // --- Part 2: name classifier ---------------------------------------------

  async preview(text: string): Promise<{
    recognized: number;
    valid: number;
    duplicates: number;
    invalid: number;
  }> {
    return jsonOrThrow(
      await fetch("/api/classify/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      })
    );
  },

  async startRun(text: string, ignoreCache: boolean): Promise<{ run_id: string }> {
    return jsonOrThrow(
      await fetch("/api/classify/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, ignore_cache: ignoreCache }),
      })
    );
  },

  async getRun(runId: string): Promise<any> {
    return jsonOrThrow(await fetch(`/api/classify/runs/${runId}`));
  },

  async cancelRun(runId: string): Promise<void> {
    await jsonOrThrow(
      await fetch(`/api/classify/runs/${runId}/cancel`, { method: "POST" })
    );
  },

  async listRuns(): Promise<any[]> {
    return (await jsonOrThrow(await fetch("/api/classify/runs"))).runs;
  },

  async getLogs(runId: string): Promise<any[]> {
    return (await jsonOrThrow(await fetch(`/api/classify/runs/${runId}/logs`))).logs;
  },

  async exportRun(
    runId: string,
    format: "csv" | "txt",
    bucket: string | null
  ): Promise<Blob> {
    const res = await fetch(`/api/classify/runs/${runId}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format, bucket }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.blob();
  },

  async getAiSettings(): Promise<{ settings: any; provider_base_urls: Record<string, string> }> {
    return jsonOrThrow(await fetch("/api/classify/settings"));
  },

  async saveAiSettings(data: any): Promise<{ settings: any }> {
    return jsonOrThrow(
      await fetch("/api/classify/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data }),
      })
    );
  },
};
