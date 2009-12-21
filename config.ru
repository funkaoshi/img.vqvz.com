ENV['GEM_PATH'] = '/home/ramanan/local/gems'

require 'rubygems'
require 'vendor/sinatra/lib/sinatra.rb'

Sinatra::Base.set(:run, false)
Sinatra::Base.set(:env, :production);

require 'vqvz.rb'
run Sinatra::Application
