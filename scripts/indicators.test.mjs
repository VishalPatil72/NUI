import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { transform } from 'esbuild'

const source = await readFile(new URL('../src/indicators.ts', import.meta.url), 'utf8')
const { code } = await transform(source, { loader: 'ts', format: 'esm', target: 'node18' })
const { calculateIndicators } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`)
const patternSource = await readFile(new URL('../src/patterns.ts', import.meta.url), 'utf8')
const { code: patternCode } = await transform(patternSource, { loader: 'ts', format: 'esm', target: 'node18' })
const { detectCurrentPattern } = await import(`data:text/javascript;base64,${Buffer.from(patternCode).toString('base64')}`)

function risingCandles(count) {
  return Array.from({ length: count }, (_, index) => {
    const close = 100 + index
    return {
      time: new Date(Date.UTC(2024, 0, index + 1)).toISOString().slice(0, 10),
      open: close - 0.5,
      high: close + 1,
      low: close - 1,
      close,
      volume: 1000 + index,
    }
  })
}

function candle(open, high, low, close) {
  return { time: '2026-10-30', open, high, low, close, volume: 1000 }
}

test('EMA and SMA seed from the first complete window', () => {
  const indicators = calculateIndicators(risingCandles(50))

  assert.equal(indicators.ema20[18], null)
  assert.equal(indicators.ema20[19], 109.5)
  assert.equal(indicators.sma50[48], null)
  assert.equal(indicators.sma50[49], 124.5)
})

test('RSI for a continuously rising series reaches 100', () => {
  const indicators = calculateIndicators(risingCandles(30))

  assert.equal(indicators.rsi[13], null)
  assert.equal(indicators.rsi[14], 100)
})

test('MACD signal values remain unavailable until its signal window forms', () => {
  const indicators = calculateIndicators(risingCandles(40))

  assert.equal(indicators.macd[24], null)
  assert.notEqual(indicators.macd[25], null)
  assert.equal(indicators.macdSignal[32], null)
  assert.notEqual(indicators.macdSignal[33], null)
})

test('ATR, Bollinger Bands, and volume average start after warm-up', () => {
  const indicators = calculateIndicators(risingCandles(30))

  assert.equal(indicators.atr[12], null)
  assert.equal(indicators.atr[13], 2)
  assert.equal(indicators.upperBand[18], null)
  assert.notEqual(indicators.upperBand[19], null)
  assert.equal(indicators.volumeAverage[19], 1009.5)
})

test('detects an engulfing pattern on the latest daily candle', () => {
  assert.equal(detectCurrentPattern([
    candle(12, 12.5, 9.5, 10),
    candle(9.8, 13, 9.4, 12.7),
  ]), 'Bullish Engulfing')
})

test('detects common single-candle patterns', () => {
  assert.equal(detectCurrentPattern([candle(10.1, 10.12, 8, 10)]), 'Hammer')
  assert.equal(detectCurrentPattern([candle(10, 12, 9.98, 10.1)]), 'Shooting Star')
  assert.equal(detectCurrentPattern([candle(10, 11, 9, 10.05)]), 'Doji')
})

test('detects morning and evening star patterns', () => {
  assert.equal(detectCurrentPattern([
    candle(12, 12.2, 9.8, 10),
    candle(9.8, 10.1, 9.7, 9.9),
    candle(10, 11.2, 9.9, 11.1),
  ]), 'Morning Star')
  assert.equal(detectCurrentPattern([
    candle(10, 12.2, 9.8, 12),
    candle(12.1, 12.3, 11.9, 12),
    candle(12, 12.2, 10.8, 10.9),
  ]), 'Evening Star')
})

test('reports when there is not enough pattern evidence', () => {
  assert.equal(detectCurrentPattern([]), 'No clear pattern')
  assert.equal(detectCurrentPattern([candle(10, 10, 10, 10)]), 'No clear pattern')
})
