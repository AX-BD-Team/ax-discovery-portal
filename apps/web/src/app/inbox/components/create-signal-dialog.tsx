'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { inboxApi } from '@ax/api-client'
import type { CreateSignalRequest, SignalSource, SignalChannel } from '@ax/types'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  Button,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  toast,
} from '@ax/ui'
import { SIGNAL_SOURCES, SIGNAL_CHANNELS } from '@ax/config'

interface CreateSignalDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function CreateSignalDialog({ open, onOpenChange, onSuccess }: CreateSignalDialogProps) {
  const [formData, setFormData] = useState<Partial<CreateSignalRequest>>({
    title: '',
    source: 'KT',
    channel: '데스크리서치',
    play_id: 'PLAY-001',
    pain: '',
    proposed_value: '',
    customer_segment: '',
    kpi_hypothesis: [],
    tags: [],
  })

  const createMutation = useMutation({
    mutationFn: (data: CreateSignalRequest) => inboxApi.createSignal(data),
    onSuccess: () => {
      onSuccess?.()
      onOpenChange(false)
      // Reset form
      setFormData({
        title: '',
        source: 'KT',
        channel: '데스크리서치',
        play_id: 'PLAY-001',
        pain: '',
        proposed_value: '',
        customer_segment: '',
        kpi_hypothesis: [],
        tags: [],
      })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.title || !formData.pain) {
      toast.warning('입력 오류', {
        description: 'Title과 Pain Point는 필수 입력 항목입니다.',
      })
      return
    }

    createMutation.mutate(formData as CreateSignalRequest)
  }

  const handleKpiAdd = () => {
    const kpi = prompt('Enter KPI hypothesis (e.g., "AHT 15%↓")')
    if (kpi) {
      setFormData(prev => ({
        ...prev,
        kpi_hypothesis: [...(prev.kpi_hypothesis || []), kpi],
      }))
    }
  }

  const handleTagAdd = () => {
    const tag = prompt('Enter tag')
    if (tag) {
      setFormData(prev => ({
        ...prev,
        tags: [...(prev.tags || []), tag],
      }))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Signal</DialogTitle>
          <DialogDescription>
            Add a new business opportunity signal to the inbox
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Title */}
          <div>
            <Label htmlFor="title">Title *</Label>
            <Input
              id="title"
              value={formData.title}
              onChange={e => setFormData(prev => ({ ...prev, title: e.target.value }))}
              placeholder="e.g., AI 상담원 보조 솔루션"
              required
            />
          </div>

          {/* Source & Channel */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="source">Source *</Label>
              <Select
                value={formData.source}
                onValueChange={v => setFormData(prev => ({ ...prev, source: v as SignalSource }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SIGNAL_SOURCES.map(source => (
                    <SelectItem key={source} value={source}>
                      {source}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="channel">Channel *</Label>
              <Select
                value={formData.channel}
                onValueChange={v =>
                  setFormData(prev => ({ ...prev, channel: v as SignalChannel }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SIGNAL_CHANNELS.map(channel => (
                    <SelectItem key={channel} value={channel}>
                      {channel}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Play ID */}
          <div>
            <Label htmlFor="play_id">Play ID *</Label>
            <Input
              id="play_id"
              value={formData.play_id}
              onChange={e => setFormData(prev => ({ ...prev, play_id: e.target.value }))}
              placeholder="PLAY-001"
              required
            />
          </div>

          {/* Customer Segment */}
          <div>
            <Label htmlFor="customer_segment">Customer Segment</Label>
            <Input
              id="customer_segment"
              value={formData.customer_segment}
              onChange={e =>
                setFormData(prev => ({ ...prev, customer_segment: e.target.value }))
              }
              placeholder="e.g., 금융권 대형 콜센터"
            />
          </div>

          {/* Pain Point */}
          <div>
            <Label htmlFor="pain">Pain Point *</Label>
            <textarea
              id="pain"
              value={formData.pain}
              onChange={e => setFormData(prev => ({ ...prev, pain: e.target.value }))}
              placeholder="고객의 핵심 Pain Point를 설명하세요"
              className="flex min-h-[100px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              required
            />
          </div>

          {/* Proposed Value */}
          <div>
            <Label htmlFor="proposed_value">Proposed Value</Label>
            <textarea
              id="proposed_value"
              value={formData.proposed_value}
              onChange={e => setFormData(prev => ({ ...prev, proposed_value: e.target.value }))}
              placeholder="제안하는 가치를 설명하세요"
              className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          {/* KPI Hypothesis */}
          <div>
            <Label>KPI Hypothesis</Label>
            <div className="mt-2 flex flex-wrap gap-2">
              {formData.kpi_hypothesis?.map((kpi, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700"
                >
                  {kpi}
                  <button
                    type="button"
                    onClick={() =>
                      setFormData(prev => ({
                        ...prev,
                        kpi_hypothesis: prev.kpi_hypothesis?.filter((_, i) => i !== idx),
                      }))
                    }
                    className="ml-1 text-blue-400 hover:text-blue-600"
                  >
                    ×
                  </button>
                </span>
              ))}
              <Button type="button" variant="outline" size="sm" onClick={handleKpiAdd}>
                + Add KPI
              </Button>
            </div>
          </div>

          {/* Tags */}
          <div>
            <Label>Tags</Label>
            <div className="mt-2 flex flex-wrap gap-2">
              {formData.tags?.map((tag, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center rounded-md bg-gray-50 px-2 py-1 text-xs font-medium text-gray-700"
                >
                  {tag}
                  <button
                    type="button"
                    onClick={() =>
                      setFormData(prev => ({
                        ...prev,
                        tags: prev.tags?.filter((_, i) => i !== idx),
                      }))
                    }
                    className="ml-1 text-gray-400 hover:text-gray-600"
                  >
                    ×
                  </button>
                </span>
              ))}
              <Button type="button" variant="outline" size="sm" onClick={handleTagAdd}>
                + Add Tag
              </Button>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create Signal'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
