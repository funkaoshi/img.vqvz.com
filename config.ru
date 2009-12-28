require File.dirname(__FILE__) + '/vendor/sinatra/lib/sinatra.rb'
Sinatra::Base.set(:run, false)
Sinatra::Base.set(:env, :production);

# require 'rack/cache'
# use Rack::Cache,
#     :verbose => true,
#     :metastore => "file:cache/meta",
#     :entitystore => "file:cache/body"

require 'vqvz.rb'
run Sinatra::Application