import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { MarkdownMessage } from './MarkdownMessage'

describe('MarkdownMessage', () => {
  it('sanitizes unsafe html while preserving markdown', () => {
    const { container } = render(
      <MarkdownMessage content={'**安全文本** <script>window.hacked=true</script> [链接](https://example.com)'} />,
    )
    expect(screen.getByText('安全文本')).toBeInTheDocument()
    expect(container.querySelector('script')).toBeNull()
    expect(screen.getByRole('link', { name: '链接' })).toHaveAttribute('rel', 'noopener noreferrer')
  })
})
