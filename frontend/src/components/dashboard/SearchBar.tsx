import { useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";

interface SearchBarProps {
  onSearch: (keyword: string) => void;
  defaultValue?: string;
}

export function SearchBar({ onSearch, defaultValue = "" }: SearchBarProps) {
  const [value, setValue] = useState(defaultValue);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(value);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      onSearch(value);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      <Search className="absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="text"
        placeholder="Search brands, keywords, ad copies..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        className="h-12 rounded-xl bg-muted/50 pl-12 pr-4 text-base shadow-none border-transparent focus-visible:border-brand-primary focus-visible:ring-brand-primary/20"
      />
    </form>
  );
}
