require File.join(File.dirname(__FILE__), '..', 'vqvz.rb')

require 'rack/test'
require 'webrat'
require 'spec'
require 'spec/interop/test'

# set test environment
set :environment, :test

Webrat.configure do |config|
  config.mode = :rack
end

# attach rack test methods to each test case block
class Test::Unit::TestCase
  include Rack::Test::Methods
  include Webrat::Methods
  include Webrat::Matchers
end

def app
  @app ||= Sinatra::Application
end
