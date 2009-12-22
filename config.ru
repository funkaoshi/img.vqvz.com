require 'rack/cache'
require 'sinatra'

Sinatra::Base.set(:run, false)
Sinatra::Base.set(:env, :production);

use Rack::Cache,
    :verbose => true,
    :metastore => "file:cache/meta",
    :entitystore => "file:cache/body"

require 'vqvz.rb'
run Sinatra::Application
