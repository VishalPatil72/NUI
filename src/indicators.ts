import type { Candle, IndicatorSnapshot } from './types'

export interface IndicatorSeries {
  ema20: (number | null)[]
  ema50: (number | null)[]
  ema200: (number | null)[]
  sma50: (number | null)[]
  rsi: (number | null)[]
  macd: (number | null)[]
  macdSignal: (number | null)[]
  upperBand: (number | null)[]
  lowerBand: (number | null)[]
  atr: (number | null)[]
  adx: (number | null)[]
  supertrend: (number | null)[]
  volumeAverage: (number | null)[]
}

function ema(values: number[], period: number): (number | null)[] {
  const result: (number | null)[] = Array(values.length).fill(null)
  if (values.length < period) return result
  const multiplier = 2 / (period + 1)
  let average = values.slice(0, period).reduce((sum, value) => sum + value, 0) / period
  result[period - 1] = average
  for (let i = period; i < values.length; i += 1) {
    average = (values[i] - average) * multiplier + average
    result[i] = average
  }
  return result
}

function rollingMean(values: number[], period: number): (number | null)[] {
  return values.map((_, index) => {
    if (index + 1 < period) return null
    return values.slice(index + 1 - period, index + 1).reduce((sum, value) => sum + value, 0) / period
  })
}

function calculateRsi(closes: number[], period = 14): (number | null)[] {
  const result: (number | null)[] = Array(closes.length).fill(null)
  if (closes.length <= period) return result
  let gain = 0
  let loss = 0
  for (let i = 1; i <= period; i += 1) {
    const change = closes[i] - closes[i - 1]
    gain += Math.max(change, 0)
    loss += Math.max(-change, 0)
  }
  let averageGain = gain / period
  let averageLoss = loss / period
  result[period] = averageLoss === 0 ? 100 : 100 - 100 / (1 + averageGain / averageLoss)
  for (let i = period + 1; i < closes.length; i += 1) {
    const change = closes[i] - closes[i - 1]
    averageGain = (averageGain * (period - 1) + Math.max(change, 0)) / period
    averageLoss = (averageLoss * (period - 1) + Math.max(-change, 0)) / period
    result[i] = averageLoss === 0 ? 100 : 100 - 100 / (1 + averageGain / averageLoss)
  }
  return result
}

function trueRanges(candles: Candle[]): number[] {
  return candles.map((candle, index) => {
    if (index === 0) return candle.high - candle.low
    const previousClose = candles[index - 1].close
    return Math.max(candle.high - candle.low, Math.abs(candle.high - previousClose), Math.abs(candle.low - previousClose))
  })
}

function calculateAtr(candles: Candle[], period: number): (number | null)[] {
  const ranges = trueRanges(candles)
  const result: (number | null)[] = Array(candles.length).fill(null)
  if (candles.length < period) return result
  let average = ranges.slice(0, period).reduce((sum, value) => sum + value, 0) / period
  result[period - 1] = average
  for (let i = period; i < ranges.length; i += 1) {
    average = (average * (period - 1) + ranges[i]) / period
    result[i] = average
  }
  return result
}

function calculateAdx(candles: Candle[], period = 14): (number | null)[] {
  const result: (number | null)[] = Array(candles.length).fill(null)
  if (candles.length <= period * 2) return result
  const tr = trueRanges(candles)
  const dx: (number | null)[] = Array(candles.length).fill(null)
  let smoothedTr = tr.slice(1, period + 1).reduce((sum, value) => sum + value, 0)
  let plus = 0
  let minus = 0
  for (let i = 1; i <= period; i += 1) {
    const up = candles[i].high - candles[i - 1].high
    const down = candles[i - 1].low - candles[i].low
    plus += up > down && up > 0 ? up : 0
    minus += down > up && down > 0 ? down : 0
  }
  for (let i = period; i < candles.length; i += 1) {
    if (i > period) {
      const up = candles[i].high - candles[i - 1].high
      const down = candles[i - 1].low - candles[i].low
      plus = plus - plus / period + (up > down && up > 0 ? up : 0)
      minus = minus - minus / period + (down > up && down > 0 ? down : 0)
      smoothedTr = smoothedTr - smoothedTr / period + tr[i]
    }
    if (smoothedTr === 0) continue
    const plusDi = 100 * plus / smoothedTr
    const minusDi = 100 * minus / smoothedTr
    const denominator = plusDi + minusDi
    dx[i] = denominator === 0 ? 0 : 100 * Math.abs(plusDi - minusDi) / denominator
  }
  let initial = dx.slice(period, period * 2).reduce<number>((sum, value) => sum + (value ?? 0), 0) / period
  result[period * 2 - 1] = initial
  for (let i = period * 2; i < candles.length; i += 1) {
    initial = (initial * (period - 1) + (dx[i] ?? 0)) / period
    result[i] = initial
  }
  return result
}

function calculateSupertrend(candles: Candle[], atr: (number | null)[], period = 10, factor = 3): (number | null)[] {
  const result: (number | null)[] = Array(candles.length).fill(null)
  let direction = 1
  let finalUpper = 0
  let finalLower = 0
  for (let i = 0; i < candles.length; i += 1) {
    const currentAtr = atr[i]
    if (currentAtr === null || i < period) continue
    const midpoint = (candles[i].high + candles[i].low) / 2
    const basicUpper = midpoint + factor * currentAtr
    const basicLower = midpoint - factor * currentAtr
    if (i === period) {
      finalUpper = basicUpper
      finalLower = basicLower
    } else {
      const previousClose = candles[i - 1].close
      finalUpper = basicUpper < finalUpper || previousClose > finalUpper ? basicUpper : finalUpper
      finalLower = basicLower > finalLower || previousClose < finalLower ? basicLower : finalLower
    }
    if (direction > 0 && candles[i].close < finalLower) direction = -1
    else if (direction < 0 && candles[i].close > finalUpper) direction = 1
    result[i] = direction > 0 ? finalLower : finalUpper
  }
  return result
}

export function calculateIndicators(candles: Candle[]): IndicatorSeries {
  const closes = candles.map(candle => candle.close)
  const ema12 = ema(closes, 12)
  const ema26 = ema(closes, 26)
  const macd = closes.map((_, index) => {
    if (ema12[index] === null || ema26[index] === null) return null
    return ema12[index]! - ema26[index]!
  })
  const firstMacdIndex = macd.findIndex(value => value !== null)
  const validMacd = firstMacdIndex < 0 ? [] : macd.slice(firstMacdIndex).map(value => value!)
  const validSignal = ema(validMacd, 9)
  const macdSignal = macd.map((value, index) => value === null ? null : validSignal[index - firstMacdIndex])
  const middleBand = rollingMean(closes, 20)
  const upperBand = closes.map((_, index) => {
    const mean = middleBand[index]
    if (mean === null) return null
    const window = closes.slice(index - 19, index + 1)
    const deviation = Math.sqrt(window.reduce((sum, value) => sum + (value - mean) ** 2, 0) / 20)
    return mean + 2 * deviation
  })
  const lowerBand = upperBand.map((upper, index) => {
    const mean = middleBand[index]
    return upper === null || mean === null ? null : 2 * mean - upper
  })
  const atr = calculateAtr(candles, 14)

  return {
    ema20: ema(closes, 20),
    ema50: ema(closes, 50),
    ema200: ema(closes, 200),
    sma50: rollingMean(closes, 50),
    rsi: calculateRsi(closes),
    macd,
    macdSignal,
    upperBand,
    lowerBand,
    atr,
    adx: calculateAdx(candles),
    supertrend: calculateSupertrend(candles, calculateAtr(candles, 10)),
    volumeAverage: rollingMean(candles.map(candle => candle.volume), 20),
  }
}

function last<T>(values: (T | null)[]): T | null {
  return values.length ? values[values.length - 1] : null
}

export function indicatorSnapshot(candles: Candle[], series = calculateIndicators(candles)): IndicatorSnapshot {
  const low = (length: number) => candles.length < length ? null : Math.min(...candles.slice(-length).map(candle => candle.low))
  const high = (length: number) => candles.length < length ? null : Math.max(...candles.slice(-length).map(candle => candle.high))
  return {
    ema20: last(series.ema20),
    ema50: last(series.ema50),
    ema200: last(series.ema200),
    sma50: last(series.sma50),
    rsi: last(series.rsi),
    macd: last(series.macd),
    macdSignal: last(series.macdSignal),
    upperBand: last(series.upperBand),
    lowerBand: last(series.lowerBand),
    atr: last(series.atr),
    adx: last(series.adx),
    supertrend: last(series.supertrend),
    volumeAverage: last(series.volumeAverage),
    support20: low(20),
    resistance20: high(20),
    support50: low(50),
    resistance50: high(50),
    high52Week: high(252),
    low52Week: low(252),
  }
}
