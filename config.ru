require File.dirname(__FILE__) + '/vendor/sinatra/lib/sinatra.rb'
Sinatra::Base.set(:run, false)
Sinatra::Base.set(:env, :production);

require 'vqvz.rb'
run Sinatra::Application
