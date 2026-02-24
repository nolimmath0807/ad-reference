import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { FormatType, SortType } from "@/types/ad";

interface FilterBarProps {
  format: "all" | FormatType;
  sort: SortType;
  dateFrom: string;
  dateTo: string;
  industry: string;
  onFormatChange: (format: "all" | FormatType) => void;
  onSortChange: (sort: SortType) => void;
  onDateFromChange: (date: string) => void;
  onDateToChange: (date: string) => void;
  onIndustryChange: (industry: string) => void;
  onClearFilters: () => void;
}

export function FilterBar({
  format,
  sort,
  dateFrom,
  dateTo,
  industry,
  onFormatChange,
  onSortChange,
  onDateFromChange,
  onDateToChange,
  onIndustryChange,
  onClearFilters,
}: FilterBarProps) {
  const hasActiveFilters =
    format !== "all" || sort !== "recent" || dateFrom || dateTo || industry;

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Select value={format} onValueChange={(v) => onFormatChange(v as "all" | FormatType)}>
        <SelectTrigger size="sm" className="w-[130px]">
          <SelectValue placeholder="Format" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Formats</SelectItem>
          <SelectItem value="image">Image</SelectItem>
          <SelectItem value="video">Video</SelectItem>
          <SelectItem value="carousel">Carousel</SelectItem>
          <SelectItem value="reels">Reels</SelectItem>
          <SelectItem value="text">Text</SelectItem>
        </SelectContent>
      </Select>

      <Select value={sort} onValueChange={(v) => onSortChange(v as SortType)}>
        <SelectTrigger size="sm" className="w-[130px]">
          <SelectValue placeholder="Sort by" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="recent">Recent</SelectItem>
          <SelectItem value="popular">Popular</SelectItem>
          <SelectItem value="engagement">Engagement</SelectItem>
        </SelectContent>
      </Select>

      <Input
        type="date"
        value={dateFrom}
        onChange={(e) => onDateFromChange(e.target.value)}
        placeholder="From"
        className="h-8 w-[140px] text-sm"
      />

      <Input
        type="date"
        value={dateTo}
        onChange={(e) => onDateToChange(e.target.value)}
        placeholder="To"
        className="h-8 w-[140px] text-sm"
      />

      <Input
        type="text"
        value={industry}
        onChange={(e) => onIndustryChange(e.target.value)}
        placeholder="Industry"
        className="h-8 w-[140px] text-sm"
      />

      {hasActiveFilters && (
        <Button variant="ghost" size="sm" onClick={onClearFilters} className="text-muted-foreground">
          <X className="size-3.5" />
          Clear filters
        </Button>
      )}
    </div>
  );
}
