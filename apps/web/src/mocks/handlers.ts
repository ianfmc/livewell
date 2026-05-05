import { http, HttpResponse } from 'msw';
import { mockData, mockContractDetails } from '../data/mockData';
import { mockDashboard } from '../data/mockDashboard';
import { mockBacktest } from '../data/mockBacktest';
import { mockModelHealth } from '../data/mockModelHealth';
import { mockSignals } from '../data/mockSignalTracker';

export const handlers = [
  http.get('/api/signals', () => {
    return HttpResponse.json(mockData);
  }),
  http.get('/api/dashboard', () => {
    return HttpResponse.json(mockDashboard);
  }),
  http.get<{ instrument: string; strike: string }>(
    '/api/signals/:instrument/:strike',
    ({ params }) => {
      const instrument = params.instrument.replace(/-/g, '/');
      const strike = params.strike;
      const detail = mockContractDetails.find(
        (d) => d.instrument === instrument && d.strike === strike
      );
      if (!detail) {
        return HttpResponse.json({ message: 'Not found' }, { status: 404 });
      }
      return HttpResponse.json(detail);
    }),
  http.get('/api/backtest/summary', () => {
    return HttpResponse.json(mockBacktest);
  }),
  http.get('/api/model/health', () => {
    return HttpResponse.json(mockModelHealth);
  }),
  http.get('/api/signals/tracker', () => {
    return HttpResponse.json(mockSignals);
  }),
  http.get('/api/explain/:signal_id', ({ params }) => {
    const { signal_id } = params;
    const surfaceId = `explain-${signal_id as string}`;
    const catalogId = 'https://a2ui.org/specification/v0_9/basic_catalog.json';

    const messages = [
      JSON.stringify({ version: 'v0.9', createSurface: { surfaceId, catalogId } }),
      JSON.stringify({ version: 'v0.9', updateComponents: { surfaceId, components: [
        { id: 'root', component: 'Column', children: ['header', 'trend', 'momentum', 'session', 'timing'] },
        { id: 'header', component: 'Text', text: { path: '/header' } },
        { id: 'trend', component: 'Text', text: { path: '/trend' } },
        { id: 'momentum', component: 'Text', text: { path: '/momentum' } },
        { id: 'session', component: 'Text', text: { path: '/session' } },
        { id: 'timing', component: 'Text', text: { path: '/timing' } },
      ]}}),
      JSON.stringify({ version: 'v0.9', updateDataModel: { surfaceId, path: '/header', value: `${signal_id as string} · mock` } }),
      JSON.stringify({ version: 'v0.9', updateDataModel: { surfaceId, path: '/trend', value: 'EMA 20 above EMA 50 — bullish bias.' } }),
      JSON.stringify({ version: 'v0.9', updateDataModel: { surfaceId, path: '/momentum', value: 'RSI at 58 — neutral with room to extend.' } }),
      JSON.stringify({ version: 'v0.9', updateDataModel: { surfaceId, path: '/session', value: 'London session — high quality.' } }),
      JSON.stringify({ version: 'v0.9', updateDataModel: { surfaceId, path: '/timing', value: 'buy_bullish slot — moderate risk.' } }),
    ];

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        for (const m of messages) {
          controller.enqueue(encoder.encode(`data: ${m}\n\n`));
        }
        // Hold the stream open so EventSource does not see a close as an error.
        // The hook closes the EventSource on cleanup; the stream will be
        // garbage-collected at that point.
      },
    });

    return new HttpResponse(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
    });
  }),
];
