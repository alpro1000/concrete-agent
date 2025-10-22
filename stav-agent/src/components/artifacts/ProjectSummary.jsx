import React from 'react';

const SectionCard = ({ title, children }) => (
  <div className="rounded-xl border border-sky-200 bg-sky-50 p-3 shadow-sm">
    <h4 className="text-xs font-semibold uppercase tracking-wide text-sky-600">{title}</h4>
    <div className="mt-2 space-y-2 text-sm text-slate-700">{children}</div>
  </div>
);

const KeyValueList = ({ data }) => (
  <dl className="grid grid-cols-1 gap-1 text-xs md:grid-cols-2">
    {Object.entries(data).map(([key, value]) => {
      let display = '—';

      if (Array.isArray(value)) {
        display = value.join(', ');
      } else if (typeof value === 'number') {
        display = value.toLocaleString();
      } else if (value !== undefined && value !== null && value !== '') {
        display = value;
      }

      return (
        <div key={key} className="rounded bg-white/80 px-2 py-1">
          <dt className="font-semibold text-slate-600">{key.replace(/_/g, ' ')}</dt>
          <dd className="text-slate-900">{display}</dd>
        </div>
      );
    })}
  </dl>
);

export default function ProjectSummary({ data = {}, compact = false }) {
  const {
    basic_info = {},
    scope = {},
    budget = {},
    kpe = {},
    source_documents = {},
    compliance = {},
    recommendations = [],
  } = data;

  return (
    <div className={`space-y-4 ${compact ? 'text-xs' : 'text-sm'}`}>
      {basic_info.project_name && (
        <div className="rounded-xl border border-sky-200 bg-white p-3 shadow-sm">
          <div className="text-xs uppercase text-sky-500">Projekt</div>
          <div className="text-base font-semibold text-slate-900">{basic_info.project_name}</div>
          {basic_info.location && (
            <div className="text-xs text-slate-600">{basic_info.location}</div>
          )}
        </div>
      )}

      {Object.keys(scope).length > 0 && (
        <SectionCard title="Rozsah">
          {scope.total_positions != null && (
            <div className="rounded bg-white/70 px-2 py-1 text-xs font-semibold text-slate-900">
              Pozic celkem: {scope.total_positions}
            </div>
          )}
          {Array.isArray(scope.main_sections) && scope.main_sections.length > 0 && (
            <div className="text-xs text-slate-700">
              Sekce: {scope.main_sections.join(', ')}
            </div>
          )}
          {Array.isArray(scope.main_activities) && scope.main_activities.length > 0 && (
            <ul className="grid gap-1 text-xs md:grid-cols-2">
              {scope.main_activities.map((activity, idx) => (
                <li key={`${activity.activity}-${idx}`} className="rounded bg-white/80 px-2 py-1">
                  {activity.activity}: {activity.qty}{activity.unit ? ` ${activity.unit}` : ''}
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      )}

      {Object.keys(budget).length > 0 && (
        <SectionCard title="Rozpočet">
          {budget.total_budget && (
            <div className="rounded bg-white/80 px-2 py-1 text-xs font-semibold text-slate-900">
              Celkem: {budget.total_budget.toLocaleString?.() || budget.total_budget} Kč
            </div>
          )}
          {budget.breakdown && <KeyValueList data={budget.breakdown} />}
        </SectionCard>
      )}

      {Object.keys(kpe).length > 0 && (
        <SectionCard title="KPI a rizika">
          <KeyValueList data={{
            'Cost per m²': kpe.cost_per_m2,
            'Doba trvání (týdny)': kpe.duration_weeks,
            'Velikost týmu': kpe.team_size,
            'Technika': kpe.equipment_count,
          }} />
          {Array.isArray(kpe.main_risks) && kpe.main_risks.length > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50/70 p-2 text-xs">
              <div className="font-semibold uppercase text-red-600">Hlavní rizika</div>
              <ul className="mt-1 space-y-1 text-red-700">
                {kpe.main_risks.map((risk, idx) => (
                  <li key={`${risk.risk}-${idx}`} className="rounded bg-white/70 px-2 py-1">
                    <div className="font-semibold">{risk.risk}</div>
                    <div className="text-xs text-red-600">
                      Pravděpodobnost: {risk.probability} • Opatření: {risk.mitigation}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </SectionCard>
      )}

      {Object.keys(source_documents).length > 0 && (
        <SectionCard title="Dokumentace">
          <KeyValueList data={source_documents} />
        </SectionCard>
      )}

      {Object.keys(compliance).length > 0 && (
        <SectionCard title="Soulad s normami">
          <KeyValueList data={compliance} />
        </SectionCard>
      )}

      {recommendations.length > 0 && (
        <SectionCard title="Doporučení">
          <ul className="list-disc space-y-1 pl-5 text-xs text-slate-700">
            {recommendations.map((recommendation, idx) => (
              <li key={`${recommendation}-${idx}`}>{recommendation}</li>
            ))}
          </ul>
        </SectionCard>
      )}
    </div>
  );
}
