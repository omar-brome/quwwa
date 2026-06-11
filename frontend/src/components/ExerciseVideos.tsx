import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Play, Search, X } from "lucide-react";
import { useRef, useState, type FormEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

/** YouTube form-video search with an inline preview player.
 * Defaults to "<exercise> form" but the query is freely editable. */
export function ExerciseVideos({ exerciseName }: { exerciseName: string }) {
  const defaultQuery = `${exerciseName} form`;
  const [query, setQuery] = useState(defaultQuery);
  const [submitted, setSubmitted] = useState(defaultQuery);
  const [activeId, setActiveId] = useState<string | null>(null);
  const playerRef = useRef<HTMLDivElement>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["videos", submitted],
    queryFn: () => api.searchVideos(submitted),
    staleTime: 24 * 60 * 60 * 1000,
    retry: 1,
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (q.length >= 2 && q !== submitted) {
      setActiveId(null);
      setSubmitted(q);
    }
  };

  const watch = (videoId: string) => {
    setActiveId(videoId);
    requestAnimationFrame(() =>
      playerRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }),
    );
  };

  const youtubeSearchUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(submitted)}`;

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <CardTitle>Form videos</CardTitle>
        <a
          href={youtubeSearchUrl}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1 text-xs text-muted-foreground"
        >
          YouTube <ExternalLink size={12} />
        </a>
      </div>

      <form onSubmit={submit} className="mb-3 flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search a movement…"
          aria-label="Search form videos"
        />
        <Button type="submit" variant="outline" size="icon" aria-label="Search">
          <Search size={16} />
        </Button>
      </form>

      {activeId && (
        <div ref={playerRef} className="relative mb-3">
          <div className="aspect-video overflow-hidden rounded-lg border border-border bg-black">
            <iframe
              className="h-full w-full"
              src={`https://www.youtube-nocookie.com/embed/${activeId}?autoplay=1&rel=0`}
              title="Form video preview"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              referrerPolicy="strict-origin-when-cross-origin"
              allowFullScreen
            />
          </div>
          <button
            onClick={() => setActiveId(null)}
            className="absolute -right-2 -top-2 flex h-7 w-7 items-center justify-center rounded-full border border-border bg-card text-muted-foreground"
            aria-label="Close preview"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex gap-3">
              <Skeleton className="h-16 w-28 shrink-0" />
              <div className="flex-1 space-y-2 py-1">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            </div>
          ))}
        </div>
      )}

      {isError && (
        <div className="space-y-2 rounded-lg bg-muted/60 p-3 text-sm text-muted-foreground">
          Couldn't reach YouTube from the server.
          <a
            href={youtubeSearchUrl}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-primary"
          >
            Open this search on YouTube <ExternalLink size={13} />
          </a>
        </div>
      )}

      {data && data.items.length === 0 && (
        <p className="py-4 text-center text-sm text-muted-foreground">
          No videos found — try different words.
        </p>
      )}

      <div className="space-y-1.5">
        {data?.items.map((v) => (
          <button
            key={v.video_id}
            onClick={() => watch(v.video_id)}
            className="flex w-full items-center gap-3 rounded-lg p-1.5 text-left active:bg-muted"
          >
            <div className="relative h-16 w-28 shrink-0 overflow-hidden rounded-lg bg-muted">
              <img
                src={v.thumbnail_url}
                alt=""
                loading="lazy"
                className="h-full w-full object-cover"
              />
              <span className="absolute inset-0 flex items-center justify-center bg-black/25">
                <Play size={20} className="fill-white text-white drop-shadow" />
              </span>
              {v.duration && (
                <Badge
                  variant="muted"
                  className="absolute bottom-1 right-1 bg-black/80 px-1 py-0 text-[10px] text-white"
                >
                  {v.duration}
                </Badge>
              )}
            </div>
            <div className="min-w-0">
              <div className="line-clamp-2 text-sm font-medium leading-snug">{v.title}</div>
              {v.channel && (
                <div className="mt-0.5 truncate text-xs text-muted-foreground">{v.channel}</div>
              )}
            </div>
          </button>
        ))}
      </div>
    </Card>
  );
}
