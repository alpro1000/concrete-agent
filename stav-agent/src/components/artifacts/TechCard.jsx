import React from 'react';

const StepCard = ({ step }) => (
  <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-3 text-xs">
    <div className="flex items-center justify-between gap-2">
      <div className="font-semibold text-amber-700">Krok {step.step_num}: {step.title}</div>
      {step.duration_minutes && (
        <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-amber-700">
          {step.duration_minutes} min
        </span>
      )}
    </div>
    <div className="mt-2 text-amber-900">{step.description}</div>
    <div className="mt-2 grid grid-cols-2 gap-1 text-[10px] text-amber-700">
      {step.workers && <div>👷 Pracovníci: {step.workers}</div>}
      {step.equipment && step.equipment.length > 0 && (
        <div>⚙️ Vybavení: {step.equipment.join(', ')}</div>
      )}
    </div>
  </div>
);

const ListSection = ({ title, items, tone = 'slate' }) => {
  if (!items || items.length === 0) return null;

  const palette = {
    slate: 'border-slate-200 bg-white/80 text-slate-700',
    green: 'border-emerald-200 bg-emerald-50/80 text-emerald-800',
    red: 'border-rose-200 bg-rose-50/80 text-rose-800',
  };

  return (
    <div className={`rounded-lg border p-3 text-xs shadow-sm ${palette[tone] || palette.slate}`}>
      <div className="font-semibold uppercase tracking-wide">{title}</div>
      <ul className="mt-1 space-y-1">
        {items.map((item, index) => (
          <li key={`${title}-${index}`} className="rounded bg-white/70 px-2 py-1">
            {typeof item === 'string' ? (
              item
            ) : (
              <div className="space-y-1">
                {item.ref && <div className="font-semibold">{item.ref}</div>}
                {item.requirement && <div className="text-[11px]">{item.requirement}</div>}
                {item.tolerance && <div className="text-[10px] text-slate-500">Tolerance: {item.tolerance}</div>}
                {item.tolerances && (
                  <div className="text-[10px] text-slate-500">Tolerance: {item.tolerances.join(', ')}</div>
                )}
                {item.timing && (
                  <div className="text-[10px] text-slate-500">Termín: {item.timing}</div>
                )}
                {item.pass && (
                  <div className="text-[10px] text-slate-500">Akceptace: {item.pass}</div>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default function TechCard({ data = {}, compact = false }) {
  const {
    title,
    position_code,
    description,
    steps = [],
    norms = [],
    quality_checks = [],
    safety_requirements = [],
    materials_used = [],
    sources = [],
  } = data;

  return (
    <div className={`space-y-4 ${compact ? 'text-xs' : 'text-sm'}`}>
      <div className="rounded-xl border border-amber-200 bg-white p-3 shadow-sm">
        <div className="text-xs uppercase text-amber-600">Technologický postup</div>
        <div className="text-base font-semibold text-amber-900">{title}</div>
        {position_code && (
          <div className="font-mono text-xs text-amber-700">Pozice: {position_code}</div>
        )}
        {description && <div className="mt-1 text-sm text-amber-800">{description}</div>}
      </div>

      {steps.length > 0 && (
        <div className="space-y-2">
          {steps.map((step) => (
            <StepCard key={step.step_num} step={step} />
          ))}
        </div>
      )}

      <ListSection title="Normy" items={norms} tone="slate" />
      <ListSection title="Kontroly kvality" items={quality_checks} tone="green" />
      <ListSection title="Bezpečnost" items={safety_requirements} tone="red" />

      {materials_used.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-3 text-xs shadow-sm">
          <div className="font-semibold uppercase tracking-wide text-amber-700">Materiály</div>
          <ul className="mt-1 space-y-1 text-amber-900">
            {materials_used.map((material, index) => (
              <li key={`${material.material}-${index}`} className="rounded bg-white/70 px-2 py-1">
                {material.material}: {material.qty}{material.unit ? ` ${material.unit}` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      {sources.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white/80 p-3 text-[10px] text-slate-600">
          Zdroje: {sources.map((source) => source.ref || source).join(', ')}
        </div>
      )}
    </div>
  );
}
