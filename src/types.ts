export interface Candle {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface IndicatorSnapshot {
  ema20: number | null
  ema50: number | null
  ema200: number | null
  sma50: number | null
  rsi: number | null
  macd: number | null
  macdSignal: number | null
  upperBand: number | null
  lowerBand: number | null
  atr: number | null
  adx: number | null
  supertrend: number | null
  volumeAverage: number | null
  support20: number | null
  resistance20: number | null
  support50: number | null
  resistance50: number | null
  high52Week: number | null
  low52Week: number | null
}

export interface Factor {
  name: string
  score: number
  reason: string
}

export interface Analysis {
  factors: Factor[]
  score: number
  signal: string
  confidence: number
  indicators: IndicatorSnapshot
  volumeSpike: boolean
  regimeWarning: boolean
}
