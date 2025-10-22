import React from 'react';

const SummaryCard = ({ title, value, hint }) => (
  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
    <div className="font-semibold uppercase tracking-wide text-slate-500">{title}</div>
    <div className="text-lg font-bold text-slate-900">{value}</div>
    {hint && <div className="mt-1 text-[11px] text-slate-500">{hint}</div>}
  </div>
);

export default function MaterialsDetailed({ data = {}, compact = false }) {
  const { materials = [], summary = {} } = data;

  return (
    <div className={`space-y-4 ${compact ? 'text-xs' : 'text-sm'}`}>
      {summary && (
        <div className="grid grid-cols-2 gap-3">
          <SummaryCard title="Materiálů celkem" value={summary.total_materials ?? '-'} />
          <SummaryCard
            title="Kritické materiály"
            value={(summary.critical_materials || []).join(', ') || 'Žádné'}
            hint="Doporučeno sledovat dostupnost"
          />
          <SummaryCard
            title="Typy"
            value={(summary.material_types || []).length}
            hint={(summary.material_types || []).join(', ')}
          />
          <SummaryCard
            title="Odhad nákladů"
            value={summary.total_cost ? `${summary.total_cost.toLocaleString()} Kč` : '—'}
          />
        </div>
      )}

      <div className="space-y-3">
        {materials.map((material) => (
          <div
            key={material.id || material.brand || material.type}
            className="rounded-lg border border-orange-200 bg-orange-50/60 p-3 shadow-sm"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <div className="text-xs uppercase text-orange-600">{material.type}</div>
                <div className="text-base font-semibold text-orange-900">
                  {material.brand || material.name || 'Neznámý materiál'}
                </div>
              </div>
              {material.quantity && (
                <div className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-orange-700">
                  {material.quantity.total ?? material.total_quantity ?? '-'}{' '}
                  {material.quantity.unit || material.unit || ''}
                </div>
              )}
            </div>

            {material.characteristics && (
              <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] text-slate-700">
                {Object.entries(material.characteristics).map(([key, value]) => (
                  <div key={key} className="rounded border border-slate-200 bg-white/70 px-2 py-1">
                    <span className="font-semibold capitalize">{key.replace(/_/g, ' ')}:</span> {value}
                  </div>
                ))}
              </div>
            )}

            {material.variants && material.variants.length > 0 && (
              <div className="mt-2 text-[11px] text-slate-700">
                <div className="font-semibold uppercase text-slate-500">Varianty</div>
                <ul className="mt-1 space-y-1">
                  {material.variants.map((variant) => (
                    <li key={`${variant.diameter}-${variant.unit}`} className="rounded bg-white/70 px-2 py-1">
                      {variant.diameter}: {variant.qty} {variant.unit}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {material.used_in && material.used_in.length > 0 && (
              <div className="mt-3 text-[11px] text-slate-700">
                <div className="font-semibold uppercase text-slate-500">Použití</div>
                <ul className="mt-1 space-y-1">
                  {material.used_in.map((usage, index) => (
                    <li key={`${usage.section}-${usage.work}-${index}`} className="rounded bg-white/70 px-2 py-1">
                      {usage.section}: {usage.work} ({usage.qty}{usage.unit ? ` ${usage.unit}` : ''})
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {material.suppliers && material.suppliers.length > 0 && (
              <div className="mt-3 text-[11px] text-slate-700">
                <div className="font-semibold uppercase text-slate-500">Dodavatelé</div>
                <ul className="mt-1 space-y-1">
                  {material.suppliers.map((supplier, index) => (
                    <li key={`${supplier.name}-${index}`} className="rounded bg-white/70 px-2 py-1">
                      <div className="font-semibold text-slate-900">{supplier.name}</div>
                      <div className="text-slate-600">
                        {supplier.distance && <span>Vzdálenost: {supplier.distance} • </span>}
                        {supplier.price && <span>Cena: {supplier.price.toLocaleString()} Kč • </span>}
                        {supplier.delivery && <span>Doprava: {supplier.delivery}</span>}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {material.sources && material.sources.length > 0 && (
              <div className="mt-3 text-[10px] text-slate-500">
                Zdroje: {material.sources.join(', ')}
              </div>
            )}
          </div>
        ))}

        {materials.length === 0 && (
          <div className="rounded border border-dashed border-slate-200 p-4 text-center text-xs text-slate-500">
            Žádné materiály k zobrazení.
          </div>
        )}
      </div>
    </div>
  );
}
