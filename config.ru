ENV['GEM_HOME'] = '/home/ramanan/local/gems'
ENV['GEM_PATH'] = '$GEM_HOME:/usr/lib/ruby/gems/1.8'  
require 'rubygems'
Gem.clear_paths

require 'vendor/sinatra/lib/sinatra.rb'

Sinatra::Base.set(:run, false)
Sinatra::Base.set(:env, :production);

require 'vqvz.rb'
run Sinatra::Application
