require File.join(File.dirname(__FILE__), '..', 'vqvz.rb')

require 'rack/test'
require 'spec'
require 'spec/interop/test'

# set test environment
set :environment, :test

# attach rack test methods to each test case block
class Test::Unit::TestCase
  include Rack::Test::Methods
end

def app
  @app ||= Sinatra::Application
end

