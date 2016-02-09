#!/usr/bin/env ruby
require 'asciidoctor'

# What's ruby doing in a python library? Good question. The protocol information is documented
# in an asciidoc file, on the web at http://catb.org/gpsd/AIVDM.txt and included here. I can't
# find a good asciidoc library for python, so this ruby script is used to extract useful info
# from the protocol docs and turn it into JSON so the decoders can be built automatically.
#
# This is all a little ugly, but hopefully it will need to be used very rarely.

class ProtocolTable
  attr_reader :title, :headers, :rows

  def initialize(adt)
    @title = adt.title
    @headers = adt.rows.head[0].map { |c| c.text }
    @rows = adt.rows.body.map { |r| r.map { |c| c.text } }
    validate_headers
  end

  EXPECTED_HEADERS = %w(Field Len Description Member T Units)

  def validate_headers
    EXPECTED_HEADERS.zip(@headers).each do |expected, actual|
      raise "suspicious headers for #{@title}: #{expected} != #{actual}" unless expected==actual
    end
  end

  def fields_as_structure
    rows.map do |row|
      result = Hash[@headers.zip(row).map { |key, value| [key.downcase, value] }]
      s, e = row[0].split('-')
      result['start'] = s.to_i
      result['end'] = e.to_i
      result['len'] = result['len'].to_i
      result
    end
  end

  def as_structure
    {
        name: @title,
        messages: fields_as_structure
    }

  end
end


def find_doc_tables(block, default_title=nil)
  result = []
  if block.blocks?
    if block.title =~ /Type 7/
      puts("#{block.level} #{block.title}")
    end
    if block.render =~ /Type 7: Binary Acknowledge/
      puts ("-----foo-----")
      puts("#{block.level} #{block.render}")
      puts ("-----foo-----")
    end
    block.blocks.each do |child|
      if child.is_a? Asciidoctor::Table
        result << child
      end
      if child.blocks?
        result.concat(find_doc_tables(child))
      end
    end
  end
  result
end

doc = Asciidoctor.load(File.new('AIVDM.txt'))
doc_tables = find_doc_tables(doc)
doc_tables.each do |t|
  title = t.title
  if not title
    if t.level == 2
      title = t.parent.title
    else
      title == t.parent.parent.title
    end
  end
  # puts("#{t.level}\t#{title}\t#{t.title}\t#{t.parent.title}")
  # puts t.title
end
exit 0

sec = doc.blocks.last.blocks[18]

table = sec.blocks[1]

t = ProtocolTable.new(table)

require 'json'


results = {"message types": {"1": t.as_structure, "2": t.as_structure, "3": t.as_structure}}
puts(JSON.pretty_generate(results))
