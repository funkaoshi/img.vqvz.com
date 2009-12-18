ENV['GEM_PATH'] = '/home/ramanan/local/gems'

require 'rubygems'
require 'sinatra'

Sinatra::Application.default_options.merge!(
      :run => false,
      :env => :development
      )

require 'vqvz.rb'
run Sinatra.application
