
interface SegmentOption<T extends string> {
  value: T;
  label: string;
}

interface SegmentedControlProps<T extends string> {
  options: SegmentOption<T>[];
  value: T;
  onChange: (val: T) => void;
  size?: 'sm' | 'md';
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  size = 'md',
}: SegmentedControlProps<T>) {
  const isSm = size === 'sm';
  return (
    <div
      className="segmented-control"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px',
        backgroundColor: 'var(--raised, #151B15)',
        border: '1px solid var(--border, #263124)',
        borderRadius: '5px',
        gap: '2px',
      }}
      role="radiogroup"
    >
      {options.map((opt) => {
        const isSelected = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={isSelected}
            onClick={() => onChange(opt.value)}
            style={{
              padding: isSm ? '3px 8px' : '5px 12px',
              backgroundColor: isSelected ? 'var(--elevated, #1D251E)' : 'transparent',
              border: '1px solid',
              borderColor: isSelected ? 'var(--border-strong, #384635)' : 'transparent',
              borderRadius: '3px',
              color: isSelected ? 'var(--text-primary, #F0F3EF)' : 'var(--text-secondary, #A0AAA0)',
              fontSize: '11px',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: isSelected ? 650 : 500,
              cursor: 'pointer',
              transition: 'background-color 140ms ease, color 140ms ease',
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
