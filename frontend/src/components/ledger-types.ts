export interface LedgerColumn {
  key: string;
  label: string;
  width?: number;
}

export interface LedgerField {
  key: string;
  label: string;
  type?: "text" | "number" | "date" | "select" | "textarea";
  options?: string[];
  span?: number;
}
