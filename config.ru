ENV['GEM_PATH'] = '/home/ramanan/local/gems'

require 'rubygems'
require 'vendor/sinatra/lib/sinatra.rb'

Sinatra::Application.default_options.merge!(
      :run => false,
      :env => :development
      )

require 'vqvz.rb'
run Sinatra.application
