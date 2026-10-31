import type { Candle } from './types'

function bodySize(candle: Candle): number {
  return Math.abs(candle.close - candle.open)
}

function rangeSize(candle: Candle): number {
  return candle.high - candle.low
}

export function detectCurrentPattern(candles: Candle[]): string {
  if (!candles.length) return 'No clear pattern'
  const current = candles[candles.length - 1]
  const previous = candles[candles.length - 2]
  const beforePrevious = candles[candles.length - 3]
  const body = bodySize(current)
  const range = rangeSize(current)
  if (range <= 0) return 'No clear pattern'

  if (previous && beforePrevious) {
    const firstBody = bodySize(beforePrevious)
    const middleBody = bodySize(previous)
    const firstMidpoint = (beforePrevious.open + beforePrevious.close) / 2
    const middleIsSmall = firstBody > 0 && middleBody <= firstBody * 0.35
    if (beforePrevious.close < beforePrevious.open && middleIsSmall
      && current.close > current.open && current.close > firstMidpoint) return 'Morning Star'
    if (beforePrevious.close > beforePrevious.open && middleIsSmall
      && current.close < current.open && current.close < firstMidpoint) return 'Evening Star'
  }

  if (previous && previous.close < previous.open && current.close > current.open
    && current.open <= previous.close && current.close >= previous.open) return 'Bullish Engulfing'
  if (previous && previous.close > previous.open && current.close < current.open
    && current.open >= previous.close && current.close <= previous.open) return 'Bearish Engulfing'

  const upperShadow = current.high - Math.max(current.open, current.close)
  const lowerShadow = Math.min(current.open, current.close) - current.low
  if (lowerShadow >= body * 2 && upperShadow <= body * 0.5 && current.close >= current.low + range * 0.6) {
    return 'Hammer'
  }
  if (upperShadow >= body * 2 && lowerShadow <= body * 0.5 && current.close <= current.low + range * 0.4) {
    return 'Shooting Star'
  }
  if (body <= range * 0.1) return 'Doji'
  return 'No clear pattern'
}
