import type { Analysis, Candle, Factor } from './types'
import { calculateIndicators, indicatorSnapshot } from './indicators'

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value))
}

export function analyze(candles: Candle[], niftyCandles: Candle[] = []): Analysis | null {
  if (candles.length < 30) return null
  const series = calculateIndicators(candles)
  const indicators = indicatorSnapshot(candles, series)
  const latest = candles[candles.length - 1]
  const previous = candles[candles.length - 2]
  const factors: Factor[] = []
  const add = (name: string, score: number, reason: string) => factors.push({ name, score, reason })

  const trendScore = ((indicators.ema50 !== null && latest.close > indicators.ema50) ? 1 : -1)
    + ((indicators.ema200 !== null && latest.close > indicators.ema200) ? 1 : -1)
  const cross = indicators.ema50 !== null && indicators.ema200 !== null
    ? indicators.ema50 > indicators.ema200 ? 'golden-cross alignment' : 'death-cross alignment'
    : 'long-term averages are still forming'
  add('Trend', clamp(trendScore, -2, 2), `Price is ${trendScore > 0 ? 'above' : 'below'} key averages; ${cross}.`)

  const rsi = indicators.rsi
  const momentumScore = (rsi !== null && rsi < 35 ? 1 : rsi !== null && rsi > 70 ? -1 : rsi !== null && rsi > 50 ? 1 : -1)
    + (indicators.macd !== null && indicators.macdSignal !== null && indicators.macd > indicators.macdSignal ? 1 : -1)
  add('Momentum', clamp(momentumScore, -2, 2), `RSI ${rsi?.toFixed(1) ?? '—'}; MACD is ${indicators.macd !== null && indicators.macdSignal !== null && indicators.macd > indicators.macdSignal ? 'above' : 'below'} its signal line.`)

  const volatilityScore = indicators.upperBand !== null && indicators.lowerBand !== null
    ? latest.close > indicators.upperBand ? 2 : latest.close < indicators.lowerBand ? -2 : 0
    : 0
  add('Volatility', volatilityScore, volatilityScore === 2 ? 'Close broke above the upper Bollinger Band.' : volatilityScore === -2 ? 'Close broke below the lower Bollinger Band.' : 'Price remains within the Bollinger Bands.')

  const volumeAverage = indicators.volumeAverage ?? 0
  const volumeSpike = volumeAverage > 0 && latest.volume > volumeAverage * 1.5
  const priceUp = latest.close >= previous.close
  add('Volume', volumeSpike ? (priceUp ? 2 : -2) : priceUp ? 1 : -1, volumeSpike ? `Volume is ${Math.round(latest.volume / volumeAverage * 100)}% of its 20-day average and ${priceUp ? 'confirms' : 'does not confirm'} the move.` : `Volume is near its 20-day average; the session closed ${priceUp ? 'higher' : 'lower'}.`)

  const adxStrong = indicators.adx !== null && indicators.adx >= 25
  const supertrendBullish = indicators.supertrend !== null && latest.close > indicators.supertrend
  add('Trend strength', adxStrong ? (supertrendBullish ? 2 : -2) : supertrendBullish ? 1 : -1, `ADX ${indicators.adx?.toFixed(1) ?? '—'}; Supertrend is ${supertrendBullish ? 'bullish' : 'bearish'}.`)

  let relativeStrength = 0
  let relativeReason = 'Nifty 50 data is unavailable; relative strength is neutral.'
  if (niftyCandles.length >= 2 && candles.length >= 2) {
    const period = Math.min(63, niftyCandles.length, candles.length)
    const stockReturn = latest.close / candles[candles.length - period].close - 1
    const niftyReturn = niftyCandles[niftyCandles.length - 1].close / niftyCandles[niftyCandles.length - period].close - 1
    relativeStrength = stockReturn > niftyReturn ? 2 : -2
    relativeReason = `3-month return ${(stockReturn * 100).toFixed(1)}% vs. Nifty ${(niftyReturn * 100).toFixed(1)}%.`
  }
  add('Relative strength', relativeStrength, relativeReason)

  const rawScore = factors.reduce((sum, factor) => sum + factor.score, 0)
  const niftyAnalysis = niftyCandles.length >= 200 ? analyzeWithoutBenchmark(niftyCandles) : null
  const regimeWarning = niftyAnalysis === 'bearish'
  const score = regimeWarning && rawScore > 0 ? Math.max(0, rawScore - 2) : rawScore
  const signal = score >= 7 ? 'Strong Buy' : score >= 3 ? 'Buy' : score <= -7 ? 'Strong Sell' : score <= -3 ? 'Sell' : 'Hold'
  const confidence = Math.round(50 + Math.min(45, Math.abs(score) / 12 * 45))

  return { factors, score, signal, confidence, indicators, volumeSpike, regimeWarning }
}

function analyzeWithoutBenchmark(candles: Candle[]): 'bullish' | 'bearish' | 'neutral' {
  const series = calculateIndicators(candles)
  const current = candles[candles.length - 1].close
  const ema50 = series.ema50[series.ema50.length - 1]
  const ema200 = series.ema200[series.ema200.length - 1]
  if (ema50 !== null && ema200 !== null && current < ema50 && current < ema200) return 'bearish'
  if (ema50 !== null && ema200 !== null && current > ema50 && current > ema200) return 'bullish'
  return 'neutral'
}
