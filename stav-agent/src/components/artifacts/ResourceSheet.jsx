import React from 'react';

const SummaryTile = ({ label, value, icon, tone = 'slate' }) => {
  const palette = {
    slate: 'border-slate-200 bg-slate-50 text-slate-900',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    blue: 'border-blue-200 bg-blue-50 text-blue-900',
    amber: 'border-amber-200 bg-amber-50 text-amber-900',
  };

  return (
    <div className={`rounded-lg border p-3 text-xs shadow-sm ${palette[tone] ?? palette.slate}`}>
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <span>{icon}</span>
        <span>{label}</span>
      </div>
      <div className="mt-1 text-lg font-bold">{value}</div>
    </div>
  );
};

export default function ResourceSheet({ data = {}, compact = false }) {
  const { summary = {}, by_section = [], team_composition = {}, equipment_schedule = {}, cost_breakdown = {} } = data;

  return (
    <div className={`space-y-4 ${compact ? 'text-xs' : 'text-sm'}`}>
      <div className="grid grid-cols-2 gap-3">
        <SummaryTile
          label="Celkem člověkohodin"
          value={`${summary.total_labor_hours?.toLocaleString?.() || summary.total_labor_hours || 0} h`}
          icon="👷"
          tone="emerald"
        />
        <SummaryTile
          label="Technika"
          value={`${summary.total_equipment_hours?.toLocaleString?.() || summary.total_equipment_hours || 0} h`}
          icon="🚜"
          tone="amber"
        />
        <SummaryTile
          label="Náklady na materiál"
          value={`${summary.total_materials_cost?.toLocaleString?.() || summary.total_materials_cost || 0} Kč`}
          icon="💰"
          tone="blue"
        />
        <SummaryTile
          label="Odhadovaná délka"
          value={`${summary.estimated_duration_days || 0} dní`}
          icon="🗓️"
        />
      </div>

      {by_section.map((section) => (
        <div key={section.section} className="rounded-xl border border-lime-200 bg-lime-50 p-3 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-xs uppercase text-lime-600">{section.section}</div>
              <div className="text-base font-semibold text-lime-900">{section.section_title}</div>
            </div>
            <div className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-lime-700">
              Materiály: {section.materials_cost?.toLocaleString?.() || section.materials_cost || 0} Kč
            </div>
          </div>

          {section.labor && (
            <div className="mt-3 text-[11px] text-slate-700">
              <div className="font-semibold uppercase text-slate-500">Pracovní síla</div>
              <div className="mt-1 grid gap-2 md:grid-cols-2">
                {Object.entries(section.labor.by_trade || {}).map(([trade, info]) => (
                  <div key={trade} className="rounded border border-slate-200 bg-white/70 px-2 py-1">
                    <div className="font-semibold text-slate-900">{trade}</div>
                    <div className="text-slate-600">
                      {info.hours?.toLocaleString?.() || info.hours || 0} h • {info.workers || 0} pracovníci
                      {info.duration_days && ` • ${info.duration_days} dní`}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {section.equipment && (
            <div className="mt-3 text-[11px] text-slate-700">
              <div className="font-semibold uppercase text-slate-500">Technika</div>
              <div className="mt-1 grid gap-2 md:grid-cols-2">
                {Object.entries(section.equipment.by_type || {}).map(([equipment, details]) => (
                  <div key={equipment} className="rounded border border-slate-200 bg-white/70 px-2 py-1">
                    <div className="font-semibold text-slate-900">{equipment}</div>
                    <div className="text-slate-600">
                      {details.hours?.toLocaleString?.() || details.hours || 0} h
                      {details.daily_rate && ` • ${details.daily_rate.toLocaleString()} Kč/den`}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {section.timeline && (
            <div className="mt-3 text-[11px] text-slate-700">
              <div className="font-semibold uppercase text-slate-500">Harmonogram</div>
              <div className="rounded border border-slate-200 bg-white/70 px-3 py-2">
                {section.timeline.start_day && section.timeline.end_day && (
                  <div>
                    Den {section.timeline.start_day} → {section.timeline.end_day}
                  </div>
                )}
                {section.timeline.critical_path && (
                  <div className="text-slate-600">Kritická cesta: {section.timeline.critical_path}</div>
                )}
              </div>
            </div>
          )}
        </div>
      ))}

      {Object.keys(team_composition).length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white/80 p-3 text-[11px] text-slate-700">
          <div className="font-semibold uppercase text-slate-500">Složení týmu</div>
          <div className="mt-1 grid grid-cols-2 gap-2">
            {Object.entries(team_composition).map(([role, count]) => (
              <div key={role} className="rounded bg-slate-50 px-2 py-1 font-medium text-slate-900">
                {role}: {count}
              </div>
            ))}
          </div>
        </div>
      )}

      {Object.keys(equipment_schedule).length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white/80 p-3 text-[11px] text-slate-700">
          <div className="font-semibold uppercase text-slate-500">Plán techniky</div>
          <ul className="mt-1 space-y-1">
            {Object.entries(equipment_schedule).map(([equipment, schedule]) => (
              <li key={equipment} className="rounded bg-slate-50 px-2 py-1 font-medium text-slate-900">
                {equipment}: <span className="font-normal text-slate-600">{schedule}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {Object.keys(cost_breakdown).length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white/80 p-3 text-[11px] text-slate-700">
          <div className="font-semibold uppercase text-slate-500">Nákladová struktura</div>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {Object.entries(cost_breakdown).map(([category, cost]) => (
              <div key={category} className="rounded bg-slate-50 px-2 py-1 font-medium text-slate-900">
                {category}: {cost.toLocaleString?.() || cost} Kč
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
