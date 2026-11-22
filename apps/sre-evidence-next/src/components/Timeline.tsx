import React from 'react';
import { RollbackEvent } from '../lib/types';
import { StatusBadge } from './StatusBadge';

interface TimelineProps {
  events: RollbackEvent[];
}

export const Timeline: React.FC<TimelineProps> = ({ events }) => {
  return (
    <div className="relative border-l-2 border-slate-800 ml-4 pl-6 space-y-6">
      {events.map((event, idx) => {
        const isFault = event.name === 'fault_detected';
        const isRollback = event.name === 'rollback_verified';
        const isBadDeploy = event.name === 'bad_image_deployed';

        return (
          <div key={idx} className="relative group">
            {/* Timeline dot */}
            <div
              className={`absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full border-2 ${
                isFault
                  ? 'bg-rose-500 border-rose-300 ring-4 ring-rose-950'
                  : isRollback
                  ? 'bg-emerald-500 border-emerald-300 ring-4 ring-emerald-950'
                  : isBadDeploy
                  ? 'bg-amber-500 border-amber-300 ring-4 ring-amber-950'
                  : 'bg-blue-500 border-blue-300 ring-4 ring-blue-950'
              }`}
            />

            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 transition-colors hover:border-slate-700">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <span className="font-mono text-sm font-bold text-slate-200">
                  {event.name}
                </span>
                <span className="font-mono text-xs text-slate-500">
                  {event.timestamp_utc}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs mt-3 pt-3 border-t border-slate-800/80">
                {event.ready_replicas !== undefined && (
                  <div>
                    <span className="text-slate-500 block">Ready Replicas:</span>
                    <span
                      className={`font-mono font-semibold ${
                        event.ready_replicas === 2 ? 'text-emerald-400' : 'text-amber-400'
                      }`}
                    >
                      {event.ready_replicas}/2
                    </span>
                  </div>
                )}

                {event.http_status !== undefined && (
                  <div>
                    <span className="text-slate-500 block">HTTP Health:</span>
                    <span
                      className={`font-mono font-semibold ${
                        event.http_status === 200 ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {event.http_status} OK
                    </span>
                  </div>
                )}

                {event.duration_seconds !== undefined && (
                  <div>
                    <span className="text-slate-500 block">Command Duration:</span>
                    <span className="font-mono font-bold text-cyan-400">
                      {event.duration_seconds}s
                    </span>
                  </div>
                )}

                {event.reason && (
                  <div>
                    <span className="text-slate-500 block">K8s Reason:</span>
                    <StatusBadge status={event.reason} variant="warning" />
                  </div>
                )}
              </div>

              {event.pod && (
                <div className="mt-2 text-xs font-mono text-slate-400">
                  <span className="text-slate-500">Affected Pod: </span>
                  {event.pod}
                </div>
              )}

              {event.image && (
                <div className="mt-2 text-xs font-mono text-slate-400 break-all">
                  <span className="text-slate-500">Target Image: </span>
                  {event.image}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
