import type { SourceInfo } from '../types'
import { FileText, ExternalLink } from 'lucide-react'

interface SourceCardProps {
  sources: SourceInfo[]
}

export default function SourceCard({ sources }: SourceCardProps) {
  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-3 pt-3 border-t border-nature-200">
      <p className="text-xs font-semibold text-wood-400 mb-2 uppercase tracking-wider">引用来源</p>
      <div className="space-y-1.5">
        {sources.map((s, i) => (
          <div
            key={i}
            className="flex items-start gap-2.5 p-2.5 bg-nature-100/50 rounded-lg text-xs group hover:bg-nature-100 transition-all"
          >
            <FileText className="w-3.5 h-3.5 text-leaf-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] text-wood-400 flex-shrink-0">[{i + 1}]</span>
                {s.kb_name && (
                  <span className="px-1.5 py-0.5 rounded-md bg-leaf-100 text-leaf-700 text-[10px] font-medium">
                    {s.kb_name}
                  </span>
                )}
                <span className="font-medium text-nature-700 truncate">{s.document_name}</span>
                {s.page > 0 && (
                  <span className="text-wood-400 flex-shrink-0">第 {s.page} 页</span>
                )}
              </div>
              <p className="text-wood-400 mt-0.5 line-clamp-1">{s.text_snippet}</p>
            </div>
            <ExternalLink className="w-3 h-3 text-wood-300 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        ))}
      </div>
    </div>
  )
}
