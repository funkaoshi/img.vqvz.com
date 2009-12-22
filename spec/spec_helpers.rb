require 'rubygems'
require 'rack/test'
require 'spec'
require 'spec/autorun'
require 'spec/interop/test'

require File.join(File.dirname(__FILE__), '..', 'vqvz.rb')

# set test environment
set :environment, :test
set :run, false
set :raise_errors, true
set :logging, false
