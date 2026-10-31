<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { createChart, type IChartApi, type ISeriesApi, type LineData, type Time } from 'lightweight-charts'
import { apiUrl } from './api'
import { calculateIndicators } from './indicators'
import { detectCurrentPattern } from './patterns'
import { analyze } from './signals'
import type { Candle } from './types'

interface StockMatch {
  symbol: string
  name: string
  exchange: string
}

interface HistoryResponse {
  symbol: string
  exchange: string
  source: string
  adjusted: boolean
  bars: Candle[]
}

interface ScanRow {
  symbol: string
  name: string
  exchange: string
  close: number
  time: string
  signal: string
  score: number
  rsi: number | null
  volumeSpike: boolean
  pattern: string
}

interface ScanError {
  symbol: string
  message: string
}

type ScanUniverse = 'NIFTY50' | 'NIFTY100' | 'MIDCAP150' | 'STARTER'

const periods = ['3M', '6M', '1Y', '2Y', '5Y']
const scanUniverses: ScanUniverse[] = ['NIFTY50', 'NIFTY100', 'MIDCAP150', 'STARTER']
const scanUniverseLabels: Record<ScanUniverse, string> = {
  NIFTY50: 'NIFTY 50',
  NIFTY100: 'NIFTY 100',
  MIDCAP150: 'NIFTY MIDCAP 150',
  STARTER: 'Starter list',
}
const scanUniverseSizes: Record<ScanUniverse, number> = {
  NIFTY50: 50,
  NIFTY100: 100,
  MIDCAP150: 150,
  STARTER: 19,
}
const symbol = ref('RELIANCE')
const exchange = ref('NSE')
const period = ref('6M')
const style = ref('Swing')
const query = ref('RELIANCE')
const suggestions = ref<StockMatch[]>([])
const candles = ref<Candle[]>([])
const niftyCandles = ref<Candle[]>([])
const source = ref('')
const error = ref('')
const loading = ref(false)
const isCsv = ref(false)
const capital = ref(100000)
const riskPercent = ref(1)
const minimumPrice = ref(200)
const minimumVolume = ref(100000)
const scanUniverse = ref<ScanUniverse>('NIFTY50')
const scanCompleted = ref(0)
const scanTotal = ref(0)
const scanRows = ref<ScanRow[]>([])
const scanErrors = ref<ScanError[]>([])
const scanLoading = ref(false)
const scanComplete = ref(false)
const scanFilter = ref('All')
const scanSort = ref<'score' | 'price' | 'symbol'>('score')
const overlays = ref({ ema: true, bands: true, supertrend: true })
const watchlist = ref<string[]>([])
const darkMode = ref(true)
const chartElement = ref<HTMLDivElement | null>(null)
const volumeElement = ref<HTMLDivElement | null>(null)
let candleChart: IChartApi | null = null
let volumeChart: IChartApi | null = null

const analysis = computed(() => analyze(candles.value, niftyCandles.value))
const latest = computed(() => candles.value[candles.value.length - 1] ?? null)
const previous = computed(() => candles.value[candles.value.length - 2] ?? null)
const changePercent = computed(() => latest.value && previous.value ? (latest.value.close / previous.value.close - 1) * 100 : 0)
const relativeReturn = computed(() => {
  if (candles.value.length < 2 || niftyCandles.value.length < 2) return null
  const count = Math.min(63, candles.value.length, niftyCandles.value.length)
  const stockStart = candles.value[candles.value.length - count].close
  const niftyStart = niftyCandles.value[niftyCandles.value.length - count].close
  const stockChange = (candles.value[candles.value.length - 1].close / stockStart - 1) * 100
  const niftyChange = (niftyCandles.value[niftyCandles.value.length - 1].close / niftyStart - 1) * 100
  return stockChange - niftyChange
})
const indicators = computed(() => analysis.value?.indicators ?? null)
const visibleScanRows = computed(() => {
  const rows = scanRows.value.filter(row => {
    const category = row.signal.includes('Buy') ? 'Buy' : row.signal.includes('Sell') ? 'Sell' : 'Hold'
    return scanFilter.value === 'All' || category === scanFilter.value
  })
  return rows.sort((a, b) => scanSort.value === 'price'
    ? b.close - a.close
    : scanSort.value === 'symbol'
      ? a.symbol.localeCompare(b.symbol)
      : b.score - a.score)
})
const isPositive = computed(() => (analysis.value?.score ?? 0) > 0)
const tradePlan = computed(() => {
  const bar = latest.value
  const atr = indicators.value?.atr
  if (!bar || !atr) return null
  const long = (analysis.value?.score ?? 0) >= 0
  const riskUnit = atr * 1.5
  const entryLow = bar.close - atr * 0.25
  const entryHigh = bar.close + atr * 0.25
  const swing = long ? indicators.value?.support20 : indicators.value?.resistance20
  const stop = roundTick(long
    ? Math.min(bar.close - riskUnit, swing ?? bar.close - riskUnit)
    : Math.max(bar.close + riskUnit, swing ?? bar.close + riskUnit))
  const perShareRisk = Math.max(Math.abs(bar.close - stop), 0.05)
  return {
    entryLow: roundTick(entryLow),
    entryHigh: roundTick(entryHigh),
    stop,
    targetOne: roundTick(bar.close + (long ? 1 : -1) * perShareRisk * 1.5),
    targetTwo: roundTick(bar.close + (long ? 1 : -1) * perShareRisk * 2.5),
    long,
    quantity: Math.floor((Math.max(0, capital.value) * Math.max(0, riskPercent.value) / 100) / perShareRisk),
    perShareRisk,
  }
})

const signalClass = computed(() => (analysis.value?.signal ?? 'Hold').toLowerCase().replace(' ', '-'))
const marketStatus = computed(() => {
  if (!latest.value) return 'Waiting for data'
  return isCsv.value ? 'CSV data loaded' : `${source.value || 'Market data'} · adjusted daily`
})
const scanUniverseTitle = computed(() => `${scanUniverseLabels[scanUniverse.value]} · ${scanUniverseSizes[scanUniverse.value]} stocks`)

function money(value: number | null | undefined): string {
  return value === null || value === undefined || !Number.isFinite(value)
    ? '—'
    : `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function roundTick(value: number): number {
  return Math.round(value / 0.05) * 0.05
}

function compact(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—'
  return value.toLocaleString('en-IN', { maximumFractionDigits: 2 })
}

async function loadHistory(nextSymbol = symbol.value): Promise<void> {
  if (!nextSymbol.trim()) return
  loading.value = true
  error.value = ''
  isCsv.value = false
  symbol.value = nextSymbol.trim().toUpperCase().replace(/\.(NS|BO)$/i, '')
  query.value = symbol.value
  candles.value = []
  niftyCandles.value = []
  try {
    const stockResponse = await fetch(apiUrl(`/api/history/${encodeURIComponent(symbol.value)}?period=${period.value}&exchange=${exchange.value}`))
    if (!stockResponse.ok) {
      const body = await stockResponse.json().catch(() => null)
      throw new Error(body?.detail || `Could not load ${symbol.value} (${stockResponse.status}).`)
    }
    const stock = await stockResponse.json() as HistoryResponse
    candles.value = stock.bars
    source.value = stock.source
    const benchmarkResponse = await fetch(apiUrl('/api/history/%5ENSEI?period=1Y&exchange=NSE'))
    if (benchmarkResponse.ok) {
      const benchmark = await benchmarkResponse.json() as HistoryResponse
      niftyCandles.value = benchmark.bars
    }
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : 'Market data could not be loaded.'
  } finally {
    loading.value = false
  }
}

async function scanMarket(): Promise<void> {
  scanLoading.value = true
  scanComplete.value = false
  scanRows.value = []
  scanErrors.value = []
  scanCompleted.value = 0
  scanTotal.value = 0
  scanFilter.value = 'All'
  try {
    const universeResponse = await fetch(apiUrl(`/api/universe?index=${scanUniverse.value}`))
    if (!universeResponse.ok) throw new Error(`Could not load stock universe (${universeResponse.status}).`)
    const universe = await universeResponse.json() as StockMatch[]
    scanTotal.value = universe.length
    const benchmarkResponse = await fetch(apiUrl('/api/history/%5ENSEI?period=1Y&exchange=NSE'))
    if (!benchmarkResponse.ok) throw new Error(`Could not load Nifty 50 benchmark (${benchmarkResponse.status}).`)
    const benchmark = await benchmarkResponse.json() as HistoryResponse
    let nextIndex = 0
    const workers = Array.from({ length: Math.min(3, universe.length) }, async () => {
      while (nextIndex < universe.length) {
        const match = universe[nextIndex]
        nextIndex += 1
        try {
          const response = await fetch(apiUrl(`/api/history/${encodeURIComponent(match.symbol)}?period=1Y&exchange=${match.exchange}`))
          if (!response.ok) {
            const body = await response.json().catch(() => null)
            throw new Error(body?.detail || `Market data request failed (${response.status}).`)
          }
          const history = await response.json() as HistoryResponse
          const result = analyze(history.bars, benchmark.bars)
          const current = history.bars[history.bars.length - 1]
          if (!result || !current) throw new Error('Not enough daily history to calculate indicators.')
          if (current.close < minimumPrice.value) continue
          if ((result.indicators.volumeAverage ?? 0) < minimumVolume.value) continue
          scanRows.value.push({
            symbol: match.symbol,
            name: match.name,
            exchange: match.exchange,
            close: current.close,
            time: current.time,
            signal: result.signal,
            score: result.score,
            rsi: result.indicators.rsi,
            volumeSpike: result.volumeSpike,
            pattern: detectCurrentPattern(history.bars),
          })
        } catch (reason) {
          scanErrors.value.push({
            symbol: match.symbol,
            message: reason instanceof Error ? reason.message : 'Unknown data error.',
          })
        } finally {
          scanCompleted.value += 1
        }
      }
    })
    await Promise.all(workers)
    scanComplete.value = true
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : 'Could not complete the consolidated analysis.'
  } finally {
    scanLoading.value = false
  }
}

async function findMatches(): Promise<void> {
  if (query.value.trim().length < 1) {
    suggestions.value = []
    return
  }
  try {
    const response = await fetch(apiUrl(`/api/search?q=${encodeURIComponent(query.value)}`))
    if (!response.ok) {
      const body = await response.json().catch(() => null)
      throw new Error(body?.detail || `Ticker search failed (${response.status}).`)
    }
    suggestions.value = await response.json() as StockMatch[]
  } catch (reason) {
    suggestions.value = []
    error.value = reason instanceof Error ? reason.message : 'Ticker search failed.'
  }
}

function chooseMatch(match: StockMatch): void {
  exchange.value = match.exchange
  suggestions.value = []
  void loadHistory(match.symbol)
}

function toggleWatchlist(): void {
  watchlist.value = watchlist.value.includes(symbol.value)
    ? watchlist.value.filter(item => item !== symbol.value)
    : [...watchlist.value, symbol.value]
  localStorage.setItem('trend-analyzer-watchlist', JSON.stringify(watchlist.value))
}

function selectWatchlist(item: string): void {
  void loadHistory(item)
}

function parseCsv(text: string): Candle[] {
  const lines = text.trim().split(/\r?\n/).filter(Boolean)
  if (lines.length < 2) throw new Error('The CSV needs a header row and at least one daily candle.')
  const headers = lines[0].split(',').map(value => value.trim().replace(/^"|"$/g, '').toLowerCase())
  const column = (names: string[]) => headers.findIndex(header => names.includes(header.replace(/[ _]/g, '')))
  const indexes = {
    date: column(['date', 'datetime', 'time']),
    open: column(['open']),
    high: column(['high']),
    low: column(['low']),
    close: column(['close', 'adjclose', 'adjustedclose']),
    volume: column(['volume', 'vol']),
  }
  if (Object.values(indexes).some(index => index < 0)) {
    throw new Error('CSV must include Date, Open, High, Low, Close, and Volume columns.')
  }
  return lines.slice(1).map((line, index) => {
    const values = line.split(',').map(value => value.trim().replace(/^"|"$/g, ''))
    const numeric = (key: 'open' | 'high' | 'low' | 'close' | 'volume') => Number(values[indexes[key]])
    const time = values[indexes.date]
    const candle = { time, open: numeric('open'), high: numeric('high'), low: numeric('low'), close: numeric('close'), volume: numeric('volume') }
    if (!time || !Number.isFinite(Date.parse(time))
      || Object.values(candle).some(value => typeof value === 'number' && !Number.isFinite(value))
      || candle.volume < 0 || candle.low > candle.high
      || candle.open < candle.low || candle.open > candle.high
      || candle.close < candle.low || candle.close > candle.high) {
      throw new Error(`Invalid OHLCV data on CSV row ${index + 2}.`)
    }
    return candle
  }).sort((a, b) => a.time.localeCompare(b.time))
}

async function uploadCsv(event: Event): Promise<void> {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    candles.value = parseCsv(await file.text())
    niftyCandles.value = []
    source.value = file.name
    isCsv.value = true
    error.value = ''
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : 'Could not read the selected CSV.'
  }
  ;(event.target as HTMLInputElement).value = ''
}

function seriesData(values: (number | null)[]): LineData<Time>[] {
  return values.flatMap((value, index) => value === null || !candles.value[index]
    ? []
    : [{ time: candles.value[index].time as Time, value }])
}

function destroyCharts(): void {
  candleChart?.remove()
  volumeChart?.remove()
  candleChart = null
  volumeChart = null
}

function renderCharts(): void {
  destroyCharts()
  if (!chartElement.value || !volumeElement.value || candles.value.length === 0) return
  const textColor = darkMode.value ? '#8b96a8' : '#64748b'
  const gridColor = darkMode.value ? '#1e2937' : '#e5eaf0'
  const background = darkMode.value ? '#101722' : '#ffffff'
  const options = (element: HTMLDivElement, height: number) => ({
    width: element.clientWidth,
    height,
    layout: { background: { color: background }, textColor, fontFamily: 'Inter, sans-serif' },
    grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
    rightPriceScale: { borderColor: gridColor },
    timeScale: { borderColor: gridColor, timeVisible: false },
    crosshair: { vertLine: { color: '#52647a' }, horzLine: { color: '#52647a' } },
  })
  candleChart = createChart(chartElement.value, options(chartElement.value, 350))
  const series = candleChart.addCandlestickSeries({
    upColor: '#30c48d', downColor: '#f16d79',
    borderUpColor: '#30c48d', borderDownColor: '#f16d79',
    wickUpColor: '#30c48d', wickDownColor: '#f16d79',
  })
  series.setData(candles.value.map(bar => ({
    time: bar.time as Time, open: bar.open, high: bar.high, low: bar.low, close: bar.close,
  })))
  if (analysis.value && latest.value) {
    series.setMarkers([{
      time: latest.value.time as Time,
      position: isPositive.value ? 'belowBar' : 'aboveBar',
      color: isPositive.value ? '#30c48d' : '#f16d79',
      shape: isPositive.value ? 'arrowUp' : 'arrowDown',
      text: analysis.value.signal,
    }])
  }
  const values = calculateIndicators(candles.value)
  const line = (data: (number | null)[], color: string, title: string) => {
    const lineSeries = candleChart!.addLineSeries({ color, lineWidth: 1, title, lastValueVisible: false, priceLineVisible: false })
    lineSeries.setData(seriesData(data))
  }
  if (overlays.value.ema) {
    line(values.ema20, '#f4bd50', 'EMA 20')
    line(values.ema50, '#58a6ff', 'EMA 50')
    line(values.ema200, '#bd8cff', 'EMA 200')
  }
  if (overlays.value.bands) {
    line(values.upperBand, '#65758b', 'BB upper')
    line(values.lowerBand, '#65758b', 'BB lower')
  }
  if (overlays.value.supertrend) line(values.supertrend, '#30c48d', 'Supertrend')
  candleChart.timeScale().fitContent()

  volumeChart = createChart(volumeElement.value, options(volumeElement.value, 100))
  const volumeSeries: ISeriesApi<'Histogram'> = volumeChart.addHistogramSeries({
    priceFormat: { type: 'volume' },
    priceScaleId: '',
    lastValueVisible: false,
  })
  volumeSeries.setData(candles.value.map((bar, index) => ({
    time: bar.time as Time,
    value: bar.volume,
    color: index === 0 || bar.close >= candles.value[index - 1].close ? '#30c48d88' : '#f16d7988',
  })))
  volumeChart.priceScale('').applyOptions({ scaleMargins: { top: 0.1, bottom: 0 } })
  volumeChart.timeScale().fitContent()
}

let resizeObserver: ResizeObserver | null = null
watch([candles, overlays, darkMode], async () => {
  await nextTick()
  renderCharts()
}, { deep: true })

onMounted(() => {
  const stored = localStorage.getItem('trend-analyzer-watchlist')
  if (stored) {
    try {
      const parsed: unknown = JSON.parse(stored)
      if (Array.isArray(parsed) && parsed.every(item => typeof item === 'string')) watchlist.value = parsed
    } catch {
      localStorage.removeItem('trend-analyzer-watchlist')
    }
  }
  void loadHistory()
  resizeObserver = new ResizeObserver(() => {
    candleChart?.applyOptions({ width: chartElement.value?.clientWidth ?? 0 })
    volumeChart?.applyOptions({ width: volumeElement.value?.clientWidth ?? 0 })
  })
  if (chartElement.value) resizeObserver.observe(chartElement.value)
})

onBeforeUnmount(() => {
  destroyCharts()
  resizeObserver?.disconnect()
})
</script>

<template>
  <div class="app-shell" :class="{ 'light-theme': !darkMode }" @click="suggestions = []">
    <header class="topbar">
      <a class="brand" href="#" aria-label="India Daily Trend Analyzer home">
        <span class="brand-mark">↗</span>
        <span>trend<span class="brand-light">desk</span></span>
        <span class="brand-divider"></span>
        <span class="brand-product">INDIA DAILY ANALYZER</span>
      </a>
      <div class="topbar-actions">
        <span class="market-pill"><span class="live-dot"></span> NSE · DAILY</span>
        <button class="icon-button" title="Toggle light/dark theme" @click.stop="darkMode = !darkMode">
          {{ darkMode ? '☼' : '◐' }}
        </button>
      </div>
    </header>

    <main class="page">
      <section class="page-heading">
        <div>
          <div class="eyebrow">MARKET OVERVIEW <span class="eyebrow-line"></span> {{ marketStatus }}</div>
          <h1>Daily trend analyzer</h1>
          <p>Data-driven signals for India’s equity markets.</p>
        </div>
        <div class="heading-actions">
          <label class="upload-button" for="csv-upload"><span>↑</span> Import CSV</label>
          <input id="csv-upload" class="visually-hidden" type="file" accept=".csv,text/csv" @change="uploadCsv" />
          <button class="scan-button" :disabled="scanLoading" @click="scanMarket">
            <span v-if="scanLoading" class="spinner"></span>{{ scanLoading ? 'Scanning' : '▦ Scan stocks' }}
          </button>
          <button class="primary-button" :disabled="loading" @click="loadHistory()">
            <span v-if="loading" class="spinner"></span>{{ loading ? 'Analyzing' : '↻ Refresh data' }}
          </button>
        </div>
      </section>

      <section class="controls panel">
        <div class="search-wrap" @click.stop>
          <label class="control-label" for="symbol-search">STOCK</label>
          <div class="search-input-wrap">
            <span class="search-icon">⌕</span>
            <input id="symbol-search" v-model="query" placeholder="Search a company or ticker" @input="findMatches" @keydown.enter="loadHistory(query)" />
            <select v-model="exchange" class="exchange-select" aria-label="Exchange">
              <option value="NSE">NSE</option>
              <option value="BSE">BSE</option>
            </select>
          </div>
          <div v-if="suggestions.length" class="suggestions">
            <button v-for="match in suggestions" :key="match.symbol" class="suggestion" @click="chooseMatch(match)">
              <span class="suggestion-symbol">{{ match.symbol }}</span><span>{{ match.name }}</span><small>{{ match.exchange }}</small>
            </button>
          </div>
        </div>
        <div class="control-group">
          <span class="control-label">LOOKBACK</span>
          <div class="segmented">
            <button v-for="item in periods" :key="item" :class="{ active: period === item }" @click="period = item; loadHistory()">{{ item }}</button>
          </div>
        </div>
        <div class="control-group style-control">
          <span class="control-label">TRADING STYLE</span>
          <div class="segmented">
            <button :class="{ active: style === 'Swing' }" @click="style = 'Swing'">Swing</button>
            <button :class="{ active: style === 'Positional' }" @click="style = 'Positional'">Positional</button>
          </div>
        </div>
        <button class="watch-button" :class="{ watching: watchlist.includes(symbol) }" @click="toggleWatchlist">
          {{ watchlist.includes(symbol) ? '★ Watching' : '☆ Watchlist' }}
        </button>
      </section>

      <div v-if="error" class="error-banner" role="alert">
        <span>!</span><div><strong>Couldn’t complete request</strong><p>{{ error }} You can still import an OHLCV CSV.</p></div>
        <button aria-label="Dismiss error" @click="error = ''">×</button>
      </div>

      <section class="panel screener-panel">
        <div class="section-header screener-header">
          <div>
            <h2>Consolidated analysis</h2>
            <p>Daily Buy, Sell, and Hold signals with the latest candlestick pattern.</p>
          </div>
          <span v-if="scanComplete" class="scan-summary">{{ scanRows.length }} stocks passed · {{ scanUniverseTitle }}</span>
        </div>
        <div class="screener-toolbar">
          <div class="screener-filters">
            <label class="universe-select">Universe
              <select v-model="scanUniverse">
                <option v-for="index in scanUniverses" :key="index" :value="index">{{ scanUniverseLabels[index] }} · {{ scanUniverseSizes[index] }} stocks</option>
              </select>
            </label>
            <label>Min. price <span>₹</span><input v-model.number="minimumPrice" type="number" min="0" step="50" /></label>
            <label>Min. avg volume <span>shares</span><input v-model.number="minimumVolume" type="number" min="0" step="10000" /></label>
          </div>
          <div class="screener-actions">
            <div v-if="scanComplete" class="segmented signal-filters">
              <button v-for="filter in ['All', 'Buy', 'Hold', 'Sell']" :key="filter" :class="{ active: scanFilter === filter }" @click="scanFilter = filter">{{ filter }}</button>
            </div>
            <label v-if="scanComplete" class="sort-select">Sort
              <select v-model="scanSort">
                <option value="score">Signal score</option>
                <option value="price">Price</option>
                <option value="symbol">Symbol</option>
              </select>
            </label>
            <button class="primary-button scan-action" :disabled="scanLoading" @click="scanMarket">
              <span v-if="scanLoading" class="spinner"></span>{{ scanLoading ? 'Scanning universe…' : scanComplete ? '↻ Rescan' : 'Run consolidated analysis' }}
            </button>
          </div>
        </div>
        <div v-if="scanLoading" class="scan-progress" role="status">
          <span class="spinner"></span> Scanning {{ scanUniverseTitle }}: {{ scanCompleted }} / {{ scanTotal }} stocks. This can take a minute when market data is not cached.
        </div>
        <div v-else-if="scanComplete && scanRows.length" class="table-scroll">
          <table class="scan-table">
            <thead>
              <tr><th>STOCK</th><th>LAST CLOSE</th><th>SIGNAL</th><th>SCORE</th><th>RSI · 14</th><th>VOLUME</th><th>CURRENT PATTERN</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in visibleScanRows" :key="row.symbol">
                <td>
                  <button class="table-symbol" @click="exchange = row.exchange; loadHistory(row.symbol)">
                    <strong>{{ row.symbol }}</strong><small>{{ row.name }}</small>
                  </button>
                </td>
                <td class="mono">{{ money(row.close) }}</td>
                <td><span class="table-signal" :class="row.signal.toLowerCase().replace(' ', '-')">{{ row.signal }}</span></td>
                <td class="mono" :class="row.score > 0 ? 'positive' : row.score < 0 ? 'negative' : ''">{{ row.score > 0 ? '+' : '' }}{{ row.score }}</td>
                <td class="mono">{{ row.rsi?.toFixed(1) ?? '—' }}</td>
                <td><span class="volume-status" :class="{ spike: row.volumeSpike }">{{ row.volumeSpike ? 'Spike' : 'Normal' }}</span></td>
                <td><span class="pattern-label" :class="{ 'no-pattern': row.pattern === 'No clear pattern' }">{{ row.pattern }}</span></td>
              </tr>
              <tr v-if="!visibleScanRows.length"><td class="empty-table" colspan="7">No stocks match this signal filter and minimum price/liquidity settings.</td></tr>
            </tbody>
          </table>
          <div v-if="scanErrors.length" class="scan-errors">
            {{ scanErrors.length }} stock{{ scanErrors.length === 1 ? '' : 's' }} could not be analyzed:
            <span v-for="item in scanErrors" :key="item.symbol" :title="item.message">{{ item.symbol }}</span>
          </div>
        </div>
        <div v-else-if="scanComplete" class="scan-empty">
          <strong>No stocks passed the filters.</strong> Lower the minimum price or average-volume threshold and rescan.
          <div v-if="scanErrors.length" class="scan-errors">{{ scanErrors.length }} stocks could not be analyzed; check Yahoo Finance availability and rescan.</div>
        </div>
        <div v-else class="scan-empty">Run a scan to rank the selected universe. The NIFTY 50 constituent snapshot may need updating after index reshuffles. The scan uses one year of adjusted daily history for consistent indicator warm-up.</div>
      </section>

      <section v-if="latest && analysis" class="summary-grid">
        <article class="quote-card panel">
          <div class="card-topline"><span class="symbol-label">{{ symbol }} <span class="exchange-mini">{{ exchange }}</span></span><span class="tiny-icon">⌁</span></div>
          <div class="quote-price">{{ money(latest.close) }}</div>
          <div class="quote-change" :class="changePercent >= 0 ? 'positive' : 'negative'">
            {{ changePercent >= 0 ? '▲' : '▼' }} {{ changePercent >= 0 ? '+' : '' }}{{ changePercent.toFixed(2) }}%
            <span>today</span>
          </div>
          <div class="quote-footer"><span>Daily close</span><strong>{{ latest.time }}</strong></div>
        </article>
        <article class="signal-card panel" :class="`signal-${signalClass}`">
          <div class="card-topline"><span class="card-label">TECHNICAL SIGNAL</span><span class="signal-status"><i></i> {{ style }} view</span></div>
          <div class="signal-main">
            <div class="signal-verdict"><span class="signal-arrow">{{ isPositive ? '↗' : analysis.score < 0 ? '↘' : '→' }}</span><span>{{ analysis.signal }}</span></div>
            <div class="confidence"><strong>{{ analysis.confidence }}%</strong><span>confidence</span></div>
          </div>
          <div class="confidence-track"><span :style="{ width: `${analysis.confidence}%` }"></span></div>
          <div class="score-foot"><span>Factor score</span><strong>{{ analysis.score > 0 ? '+' : '' }}{{ analysis.score }} <small>/ 12</small></strong></div>
        </article>
        <article class="metric-card panel">
          <div class="metric-title">RELATIVE STRENGTH <span class="metric-icon">◎</span></div>
          <div class="metric-value" :class="relativeReturn === null ? '' : relativeReturn >= 0 ? 'positive' : 'negative'">
            {{ relativeReturn === null ? 'Unavailable' : relativeReturn >= 0 ? 'Outperforming' : 'Underperforming' }}
          </div>
          <div class="metric-sub">{{ relativeReturn === null ? 'Benchmark data not loaded' : `${relativeReturn >= 0 ? '+' : ''}${relativeReturn.toFixed(2)}% vs. Nifty · 3M` }}</div>
          <div class="metric-bar"><span :style="{ width: relativeReturn === null ? '20%' : `${Math.max(8, Math.min(100, 50 + relativeReturn * 2))}%` }"></span></div>
        </article>
        <article class="metric-card panel">
          <div class="metric-title">VOLUME ACTIVITY <span class="metric-icon">▥</span></div>
          <div class="metric-value">{{ analysis.volumeSpike ? 'Volume spike' : 'Normal range' }}</div>
          <div class="metric-sub">{{ indicators?.volumeAverage ? `${Math.round(latest.volume / indicators.volumeAverage * 100)}% of 20-day avg` : '20-day average forming' }}</div>
          <div class="volume-mini"><span v-for="(bar, index) in candles.slice(-16)" :key="bar.time" :style="{ height: `${Math.max(14, Math.min(100, bar.volume / Math.max(...candles.slice(-16).map(item => item.volume)) * 100))}%` }" :class="index && bar.close >= candles[candles.length - 16 + index - 1].close ? 'up' : 'down'"></span></div>
        </article>
      </section>

      <section v-if="latest && analysis" class="main-grid">
        <div class="left-column">
          <article class="panel chart-panel">
            <div class="section-header chart-header">
              <div><h2>Price action</h2><p>{{ symbol }} · {{ period }} · Daily candles</p></div>
              <div class="chart-overlays">
                <button :class="{ selected: overlays.ema }" @click="overlays.ema = !overlays.ema"><i class="legend-dot ema-dot"></i> EMA</button>
                <button :class="{ selected: overlays.bands }" @click="overlays.bands = !overlays.bands"><i class="legend-dot band-dot"></i> Bands</button>
                <button :class="{ selected: overlays.supertrend }" @click="overlays.supertrend = !overlays.supertrend"><i class="legend-dot super-dot"></i> Supertrend</button>
              </div>
            </div>
            <div ref="chartElement" class="price-chart"></div>
            <div class="volume-legend"><span>VOLUME</span><strong>{{ latest.volume.toLocaleString('en-IN') }}</strong><span>20D AVG</span><strong>{{ indicators?.volumeAverage?.toLocaleString('en-IN', { maximumFractionDigits: 0 }) ?? '—' }}</strong></div>
            <div ref="volumeElement" class="volume-chart"></div>
          </article>

          <article v-if="watchlist.length" class="panel watchlist-panel">
            <div class="section-header"><div><h2>Your watchlist</h2><p>Saved on this device</p></div><span class="watch-count">{{ watchlist.length }} symbols</span></div>
            <div class="watch-items">
              <button v-for="item in watchlist" :key="item" class="watch-item" :class="{ current: item === symbol }" @click="selectWatchlist(item)">
                <span class="watch-symbol">{{ item }}</span><span>{{ item === symbol && latest ? money(latest.close) : 'Open analysis →' }}</span><span class="watch-star">★</span>
              </button>
            </div>
          </article>
        </div>

        <div class="right-column">
          <article class="panel factors-panel">
            <div class="section-header"><div><h2>Signal breakdown</h2><p>What’s driving this view</p></div><span class="factor-count">{{ analysis.factors.length }} FACTORS</span></div>
            <div class="factor-list">
              <div v-for="factor in analysis.factors" :key="factor.name" class="factor-row">
                <div class="factor-head"><span class="factor-name">{{ factor.name }}</span><span class="factor-score" :class="factor.score > 0 ? 'positive' : factor.score < 0 ? 'negative' : ''">{{ factor.score > 0 ? '+' : '' }}{{ factor.score }}</span></div>
                <p>{{ factor.reason }}</p>
                <div class="factor-track"><span :class="factor.score > 0 ? 'positive-fill' : factor.score < 0 ? 'negative-fill' : 'neutral-fill'" :style="{ width: `${Math.abs(factor.score) / 2 * 100}%` }"></span></div>
              </div>
            </div>
            <div v-if="analysis.regimeWarning" class="regime-warning"><span>⚠</span><p><strong>Bearish market regime</strong><br>Nifty 50 is below its 50 and 200-day averages. Positive signals have been downgraded.</p></div>
          </article>

          <article class="panel indicators-panel">
            <div class="section-header"><div><h2>Key indicators</h2><p>Latest daily readings</p></div><span class="live-indicator"><i></i> LIVE</span></div>
            <div class="indicator-table">
              <div><span>RSI <small>14</small></span><strong :class="(indicators?.rsi ?? 50) > 70 ? 'negative' : (indicators?.rsi ?? 50) < 30 ? 'positive' : ''">{{ compact(indicators?.rsi) }}</strong></div>
              <div><span>MACD <small>12 · 26 · 9</small></span><strong :class="(indicators?.macd ?? 0) >= (indicators?.macdSignal ?? 0) ? 'positive' : 'negative'">{{ compact(indicators?.macd) }}</strong></div>
              <div><span>ADX <small>14</small></span><strong>{{ compact(indicators?.adx) }}</strong></div>
              <div><span>ATR <small>14</small></span><strong>{{ money(indicators?.atr) }}</strong></div>
              <div><span>EMA <small>20 / 50 / 200</small></span><strong class="indicator-stack">{{ compact(indicators?.ema20) }} / {{ compact(indicators?.ema50) }} / {{ compact(indicators?.ema200) }}</strong></div>
              <div><span>SMA <small>50-day</small></span><strong>{{ compact(indicators?.sma50) }}</strong></div>
              <div><span>Bollinger <small>20-day · upper / lower</small></span><strong class="indicator-stack">{{ compact(indicators?.upperBand) }} / {{ compact(indicators?.lowerBand) }}</strong></div>
              <div><span>Supertrend <small>10, 3</small></span><strong>{{ money(indicators?.supertrend) }}</strong></div>
              <div><span>Support <small>20-day</small></span><strong>{{ money(indicators?.support20) }}</strong></div>
              <div><span>Resistance <small>20-day</small></span><strong>{{ money(indicators?.resistance20) }}</strong></div>
              <div><span>Support / resistance <small>50-day</small></span><strong class="indicator-stack">{{ money(indicators?.support50) }} / {{ money(indicators?.resistance50) }}</strong></div>
              <div><span>52-week range <small>High / low</small></span><strong class="indicator-stack">{{ money(indicators?.high52Week) }} / {{ money(indicators?.low52Week) }}</strong></div>
            </div>
          </article>

          <article class="panel trade-panel">
            <div class="section-header"><div><h2>Trade plan</h2><p>Illustrative levels · not a recommendation</p></div><span class="trade-style">{{ style.toUpperCase() }}</span></div>
            <div v-if="tradePlan" class="trade-levels">
              <div><span>Entry zone</span><strong>{{ money(tradePlan.entryLow) }} — {{ money(tradePlan.entryHigh) }}</strong></div>
              <div><span>Stop-loss</span><strong class="negative">{{ money(tradePlan.stop) }}</strong></div>
              <div><span>Target 1</span><strong class="positive">{{ money(tradePlan.targetOne) }}</strong></div>
              <div><span>Target 2</span><strong class="positive">{{ money(tradePlan.targetTwo) }}</strong></div>
              <div><span>Bias</span><strong :class="tradePlan.long ? 'positive' : 'negative'">{{ tradePlan.long ? 'Long' : 'Short' }}</strong></div>
              <div class="risk-reward"><span>Risk : reward</span><strong>1 : 1.5 / 2.5</strong></div>
            </div>
            <div class="sizing-form">
              <label>Capital <span>₹</span><input v-model.number="capital" type="number" min="0" step="10000" /></label>
              <label>Risk per trade <span>%</span><input v-model.number="riskPercent" type="number" min="0.1" max="100" step="0.1" /></label>
            </div>
            <div v-if="tradePlan" class="position-size"><span>Position size</span><strong>{{ tradePlan.quantity.toLocaleString('en-IN') }} <small>shares</small></strong></div>
          </article>
        </div>
      </section>

      <section v-else-if="loading" class="loading-panel panel"><span class="spinner large"></span><h2>Fetching daily market data</h2><p>Connecting to the data provider and calculating indicators…</p></section>
      <section v-else-if="!error" class="empty-state panel"><div class="empty-chart">⌁</div><h2>Ready when you are</h2><p>Search a ticker or import a CSV to explore daily price trends.</p></section>

      <footer class="disclaimer">
        <span class="disclaimer-icon">ⓘ</span>
        <p><strong>Important:</strong> For educational purposes only. Not investment advice. Not SEBI-registered advice. Markets involve risk. Data may be delayed or incomplete; verify independently.</p>
        <span class="footer-version">TREND DESK <span>·</span> 0.1.0</span>
      </footer>
    </main>
  </div>
</template>
