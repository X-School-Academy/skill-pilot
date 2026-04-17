export const AUTO_EXECUTE_OPTION = '__auto__';

export type ExecuteSelectOption = {
  value: string;
  label: string;
};

export const isAutoExecuteTarget = (value: string | null | undefined): boolean => value === AUTO_EXECUTE_OPTION;

export const buildExecuteSelectOptions = (items: string[]): ExecuteSelectOption[] => {
  const seen = new Set<string>();
  const options: ExecuteSelectOption[] = [{ value: AUTO_EXECUTE_OPTION, label: 'Auto' }];

  for (const item of items) {
    const value = String(item || '').trim();
    if (!value || value === AUTO_EXECUTE_OPTION || seen.has(value)) continue;
    seen.add(value);
    options.push({ value, label: value });
  }

  return options;
};
